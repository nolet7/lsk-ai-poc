"""Stage-specific bearer identity, domain authorization, and spoofing regression."""
import os
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from integrations.gateway import app
from integrations.security import Principal

class OIDCStageTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
        self.demo={"X-API-Key":"test-key","X-Actor":"forged.admin"}
        self.bearer={"Authorization":"Bearer dummy-test-token", "X-Actor":"forged.admin","X-Role":"reviewer"}

    def test_pilot_rejects_demo_identity_even_with_key(self):
        with patch.dict(os.environ,{"LSK_STAGE":"pilot","GATEWAY_API_KEY":"test-key"},clear=True):
            result=self.client.get("/v1/apps",headers=self.demo)
        self.assertEqual(result.status_code,401)

    def test_production_rejects_demo_identity_even_with_key(self):
        with patch.dict(os.environ,{"LSK_STAGE":"production","GATEWAY_API_KEY":"test-key"},clear=True):
            result=self.client.post("/v1/agent/run",headers=self.demo,json={"question":"Summarize invoices"})
        self.assertEqual(result.status_code,401)

    def test_pilot_uses_verified_subject_and_scopes_domains(self):
        principal=Principal("real.user",frozenset({"finance"}),frozenset({"lsk.ai.read"}))
        with patch.dict(os.environ,{"LSK_STAGE":"pilot"},clear=True), \
             patch("integrations.gateway.verify_oidc_token",return_value=principal), \
             patch("integrations.gateway.forward",new_callable=AsyncMock) as forward:
            forward.return_value=[{"id":"inv-1002"}]
            accepted=self.client.get("/v1/apps/finance/records",headers=self.bearer)
            denied=self.client.get("/v1/apps/sales/records",headers=self.bearer)
            self.assertEqual(accepted.status_code,200)
            self.assertEqual(denied.status_code,403)
            forward.assert_awaited_once_with("finance","/v1/records","real.user")

    def test_agent_tools_enforce_same_domain_claims(self):
        principal=Principal("real.user",frozenset({"finance"}),frozenset({"lsk.ai.read"}))
        async def fake_agent(question,actor,forward,allow_proposals=False):
            from fastapi import HTTPException
            await forward("sales","/v1/records",actor)
            return {"answer":"unreachable"}
        with patch.dict(os.environ,{"LSK_STAGE":"production"},clear=True), \
             patch("integrations.gateway.verify_oidc_token",return_value=principal), \
             patch("integrations.gateway.run_commercial_agent",side_effect=fake_agent):
            response=self.client.post("/v1/agent/run",headers=self.bearer,json={"question":"Find sales records"})
        self.assertEqual(response.status_code,403)

    def test_pilot_disallows_demo_reviewer_even_with_bearer(self):
        principal=Principal("real.user",frozenset({"finance"}),frozenset({"lsk.ai.read","lsk.ai.reviewer"}))
        with patch.dict(os.environ,{"LSK_STAGE":"pilot"},clear=True), \
             patch("integrations.gateway.verify_oidc_token",return_value=principal):
            response=self.client.post("/v1/apps/finance/proposals/one/decision",headers=self.bearer,json={"approve":True})
        self.assertEqual(response.status_code,403)
