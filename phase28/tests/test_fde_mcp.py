"""MCP SDK server auth boundary; no live network, AWS, or secrets."""
from __future__ import annotations
import os
import unittest
from unittest.mock import patch

from phase28.authorization import Principal
from phase28.oidc import AuthenticationFailed
from phase28.fde_commercial.contracts import CommercialContext

class Verifier:
    def verify(self, raw):
        if raw=="allowed":
            return Principal("alice","tenant-a",frozenset({"procurement"}))
        if raw=="finance-only":
            return Principal("frank","tenant-a",frozenset({"finance"}))
        raise AuthenticationFailed("Unauthorized")

class FakeRepo:
    def case(self,*args):
        raise AssertionError("DB tool must not execute during authentication tests")
    def evidence(self,*args):
        raise AssertionError("DB tool must not execute during authentication tests")

class MCPAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_remote_token_verification_and_domain_scope(self):
        from phase28.fde_commercial.mcp_server import SignedOIDCVerifier
        verifier=SignedOIDCVerifier(Verifier())
        self.assertIsNone(await verifier.verify_token("forged"))
        self.assertIsNone(await verifier.verify_token("finance-only"))
        accepted=await verifier.verify_token("allowed")
        self.assertEqual(accepted.subject,"alice")
        self.assertEqual(accepted.claims["tenant_id"],"tenant-a")
        self.assertIn("procurement:read",accepted.scopes)

    async def test_mcp_principal_never_uses_tool_arguments(self):
        from phase28.fde_commercial.mcp_server import current_context
        from mcp.server.auth.provider import AccessToken
        token=AccessToken(token="test",client_id="lsk",scopes=["procurement:read"],
                          subject="alice",claims={"tenant_id":"tenant-a",
                                                  "roles":["procurement"]})
        with patch("phase28.fde_commercial.mcp_server.get_access_token",return_value=token):
            ctx=current_context()
        self.assertEqual(ctx.tenant_id,"tenant-a")
        self.assertEqual(ctx.roles,frozenset({"procurement"}))
        with patch("phase28.fde_commercial.mcp_server.get_access_token",return_value=None):
            with self.assertRaises(PermissionError):
                current_context()

    async def test_sdk_server_constructs_only_read_tools(self):
        from phase28.fde_commercial.mcp_server import build_server
        environment={"LSK_MCP_PUBLIC_URL":"https://mcp.internal.example.test/mcp",
                     "LSK_MCP_PORT":"8082",
                     "LSK_OIDC_ISSUER":"https://login.example.test"}
        with patch.dict(os.environ,environment), patch(
             "phase28.fde_commercial.mcp_server.load_authority",return_value=(Verifier(),None)):
            server=build_server(FakeRepo())
        tools=server._tool_manager.list_tools()
        self.assertEqual({tool.name for tool in tools},
                         {"procurement_case_read","procurement_document_search"})

if __name__=="__main__":
    unittest.main()
