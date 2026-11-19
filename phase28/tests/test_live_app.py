"""Private AI pilot integration tests: no AWS, no network, signed local JWTs."""
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from phase28.authorization import DomainAuthorizer
from phase28.live_app import create_app, initialize_database
from phase28.oidc import OIDCVerifier


class TestLiveApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pub = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        pub.update({"kid": "pilot", "alg": "RS256", "use": "sig"})
        cls.verifier = OIDCVerifier(
            issuer="https://id.example.test/realms/lsk", audience="phase28",
            jwks={"keys": [pub]})

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "evidence.sqlite"
        initialize_database(self.db)
        with sqlite3.connect(self.db) as con:
            con.executemany("INSERT INTO sources VALUES (?,?,?,?,?)", [
                ("doc-a", "tenant-a", "orders", "order-1", "Delivery requires confirmation."),
                ("doc-b", "tenant-b", "orders", "order-2", "Other tenant secret."),
            ])
        self.bedrock = Mock()
        self.client = TestClient(self.app(False))

    def app(self, live):
        return create_app(db_path=self.db, verifier=self.verifier,
                          authorizer=DomainAuthorizer({"sales": frozenset({"orders"})}),
                          model_id="model-approved", region="us-east-1",
                          live=live, max_daily_calls=1, bedrock_client=self.bedrock)

    def token(self, tenant="tenant-a", roles=None):
        now = int(time.time())
        return jwt.encode({"iss": "https://id.example.test/realms/lsk",
                           "aud": "phase28", "sub": "alice", "tenant_id": tenant,
                           "roles": roles if roles is not None else ["sales"],
                           "iat": now - 1, "nbf": now - 1, "exp": now + 120},
                          self.key, algorithm="RS256", headers={"kid": "pilot"})

    def ask(self, client=None, tenant="tenant-a", **kwargs):
        return (client or self.client).post(
            "/v1/business/questions",
            headers={"Authorization": "Bearer " + self.token(tenant)},
            json={"domain": "orders", "question": "What is the policy?", **kwargs})

    def test_ready(self):
        self.assertEqual(self.client.get("/health/ready").status_code, 200)

    def test_unauthenticated(self):
        res = self.client.post("/v1/business/questions", json={"domain": "orders", "question": "hi"})
        self.assertEqual(res.status_code, 401)

    def test_tenant_isolation(self):
        self.assertEqual(self.ask().json()["cited_source_ids"], ["doc-a"])
        self.assertEqual(self.ask(tenant="tenant-b").json()["cited_source_ids"], ["doc-b"])

    def test_model_denied_by_default(self):
        self.assertEqual(self.ask(use_model=True).status_code, 403)
        self.bedrock.converse.assert_not_called()

    def test_unknown_role_denied(self):
        token = self.token(roles=["unknown"])
        res = self.client.post("/v1/business/questions",
                               headers={"Authorization": "Bearer " + token},
                               json={"domain": "orders", "question": "hi"})
        self.assertEqual(res.status_code, 403)

    def test_real_adapter_mocked_and_daily_cap(self):
        self.bedrock.converse.return_value = {
            "output": {"message": {"content": [{"text": json.dumps({
                "answer": "Confirmation is required.", "cited_source_ids": ["doc-a"]
            })}]}}}
        client = TestClient(self.app(True))
        first = self.ask(client=client, use_model=True)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["status"], "answered")
        self.assertEqual(self.ask(client=client, use_model=True).status_code, 429)
        self.assertEqual(self.bedrock.converse.call_count, 1)

    def test_reject_unretrieved_citation(self):
        self.bedrock.converse.return_value = {
            "output": {"message": {"content": [{"text": json.dumps({
                "answer": "Other tenant data.", "cited_source_ids": ["doc-b"]
            })}]}}}
        result = self.ask(client=TestClient(self.app(True)), use_model=True)
        self.assertEqual(result.status_code, 503)


if __name__ == "__main__":
    unittest.main()
