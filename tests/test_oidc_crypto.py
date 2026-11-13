"""Cryptographic OIDC verification tests (real RS256 signatures, mocked JWKS fetch).

No external network, IdP secrets, cloud permissions, or API keys required.
"""
import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from integrations.security import verify_oidc_token

class OIDCCryptoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.public=cls.private.public_key()
    def claims(self, **extra):
        data={"sub":"user.123","aud":"lsk-ai-api","iss":"https://identity.example.test",
              "iat":int(time.time()),"exp":int(time.time())+3600,
              "roles":["lsk.ai.read"],"domains":["finance"]}
        data.update(extra)
        return data
    def verify(self, token):
        class Client:
            def get_signing_key_from_jwt(self, _token):
                return SimpleNamespace(key=OIDCCryptoTests.public)
        with patch.dict(os.environ,{"OIDC_ISSUER":"https://identity.example.test",
                   "OIDC_AUDIENCE":"lsk-ai-api",
                   "OIDC_JWKS_URL":"https://identity.example.test/.well-known/jwks.json"},clear=True), \
             patch("integrations.security._jwks_client",return_value=Client()):
            return verify_oidc_token(token)
    def sign(self, claims, private=None):
        return jwt.encode(claims,private or self.private,algorithm="RS256",
                          headers={"kid":"test-key-1"})
    def test_valid_signed_token(self):
        result=self.verify(self.sign(self.claims()))
        self.assertEqual(result.subject,"user.123")
        self.assertEqual(result.domains,frozenset({"finance"}))
    def test_modified_payload_is_rejected(self):
        token=self.sign(self.claims())
        parts=token.split(".")
        data=jwt.api_jws.base64url_decode(parts[1].encode())
        changed=data.replace(b"user.123",b"user.999")
        parts[1]=jwt.api_jws.base64url_encode(changed).decode()
        with self.assertRaises(HTTPException) as exc:
            self.verify(".".join(parts))
        self.assertEqual(exc.exception.status_code,401)
    def test_expired_token_is_rejected(self):
        with self.assertRaises(HTTPException) as exc:
            self.verify(self.sign(self.claims(exp=int(time.time())-3600)))
        self.assertEqual(exc.exception.status_code,401)
    def test_wrong_audience_is_rejected(self):
        with self.assertRaises(HTTPException) as exc:
            self.verify(self.sign(self.claims(aud="other-api")))
        self.assertEqual(exc.exception.status_code,401)
    def test_missing_read_role_denied(self):
        with self.assertRaises(HTTPException) as exc:
            self.verify(self.sign(self.claims(roles=[])))
        self.assertEqual(exc.exception.status_code,403)
