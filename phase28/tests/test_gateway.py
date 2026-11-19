"""P28-13 HTTP tests; in-memory RSA fixture, no external OIDC or AWS calls."""
import json
import time
import unittest
from unittest.mock import Mock

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from phase28.authorization import DomainAuthorizer
from phase28.gateway import create_app
from phase28.oidc import OIDCVerifier


class TestGateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        public.update({"kid": "test-key", "alg": "RS256", "use": "sig"})
        cls.jwks = {"keys": [public]}
        cls.issuer = "https://identity.example.test/realms/lsk"
        cls.audience = "phase28-api"
        cls.verifier = OIDCVerifier(issuer=cls.issuer, audience=cls.audience, jwks=cls.jwks)

    def setUp(self):
        self.retrieve = Mock(return_value={"sources": [
            {"id": "s1", "tenant_id": "tenant-a", "domain": "orders"}
        ]})
        self.audit = Mock()
        self.client = TestClient(create_app(
            verifier=self.verifier,
            authorizer=DomainAuthorizer({"sales": frozenset({"orders"})}),
            retrieve=self.retrieve, audit_sink=self.audit,
        ))

    def token(self, **changes):
        now = int(time.time())
        payload = {"iss": self.issuer, "aud": self.audience, "sub": "alice",
                   "tenant_id": "tenant-a", "roles": ["sales"],
                   "iat": now - 1, "nbf": now - 1, "exp": now + 300}
        payload.update(changes)
        return jwt.encode(payload, self.key, algorithm="RS256", headers={"kid": "test-key"})

    def ask(self, token=None, **body):
        return self.client.post("/v1/business/questions", json={
            "question": "Status?", "domain": "orders", **body,
        }, headers={"Authorization": "Bearer " + (token if token is not None else self.token())})

    def test_liveness(self):
        self.assertEqual(self.client.get("/health/live").json(), {"status": "alive"})
        self.retrieve.assert_not_called()

    def test_valid_retrieval_only(self):
        r = self.ask()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "retrieval_only")
        self.assertEqual(r.json()["cited_source_ids"], ["s1"])
        self.assertEqual(r.json()["actions_taken"], [])
        self.assertEqual(self.audit.call_args.args[0]["outcome"], "success")

    def test_missing_token_denied(self):
        r = self.client.post("/v1/business/questions", json={"domain": "orders", "question": "Hi"})
        self.assertEqual(r.status_code, 401)
        self.retrieve.assert_not_called()

    def test_expired_token_denied(self):
        self.assertEqual(self.ask(self.token(exp=int(time.time()) - 20)).status_code, 401)
        self.retrieve.assert_not_called()

    def test_wrong_audience_denied(self):
        self.assertEqual(self.ask(self.token(aud="another-api")).status_code, 401)
        self.retrieve.assert_not_called()

    def test_wrong_issuer_denied(self):
        self.assertEqual(self.ask(self.token(iss="https://other.test")).status_code, 401)
        self.retrieve.assert_not_called()

    def test_forged_signature_denied(self):
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = int(time.time())
        forged = jwt.encode({"iss": self.issuer, "aud": self.audience, "sub": "alice",
                             "tenant_id": "tenant-a", "roles": ["sales"], "iat": now - 1,
                             "nbf": now - 1, "exp": now + 300}, other,
                            algorithm="RS256", headers={"kid": "test-key"})
        self.assertEqual(self.ask(forged).status_code, 401)
        self.retrieve.assert_not_called()

    def test_cross_tenant_source_fails_closed(self):
        self.retrieve.return_value = {"sources": [
            {"id": "s1", "tenant_id": "tenant-b", "domain": "orders"}
        ]}
        self.assertEqual(self.ask().status_code, 503)

    def test_wrong_domain_denied_before_retrieval(self):
        self.assertEqual(self.ask(domain="finance").status_code, 403)
        self.retrieve.assert_not_called()

    def test_untrusted_role_denied(self):
        self.assertEqual(self.ask(self.token(roles=["finance"])).status_code, 403)
        self.retrieve.assert_not_called()

    def test_model_flag_denied_even_with_valid_identity(self):
        self.assertEqual(self.ask(use_model=True).status_code, 403)
        self.retrieve.assert_not_called()

    def test_missing_claims_rejected(self):
        self.assertEqual(self.ask(self.token(roles=[])).status_code, 401)
        self.retrieve.assert_not_called()

    def test_unknown_kid_rejected(self):
        tok = jwt.encode({"iss": self.issuer}, self.key, algorithm="RS256", headers={"kid": "unknown"})
        self.assertEqual(self.ask(tok).status_code, 401)
        self.retrieve.assert_not_called()

    def test_configuration_rejects_non_https(self):
        with self.assertRaises(ValueError):
            OIDCVerifier(issuer="http://localhost", audience=self.audience, jwks=self.jwks)

    def test_extra_request_identity_fields_rejected(self):
        self.assertEqual(self.ask(tenant_id="tenant-b").status_code, 422)
        self.retrieve.assert_not_called()


if __name__ == "__main__":
    unittest.main()
