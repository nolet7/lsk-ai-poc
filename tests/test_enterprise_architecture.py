"""Source-grounded safety and architecture regression tests (no AWS charges)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from integrations.gateway import app
from integrations.acl_retrieval import retrieve
from integrations.enterprise_policy import scope_for
from integrations.command_store import submit, my_proposals
from integrations.bedrock_gateway import infer, ModelUnavailable
import asyncio

class CommercialArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
        self.headers={"X-API-Key":"gateway-test","X-Actor":"employee"}
        self.environ=patch.dict(os.environ,{
            "LSK_STAGE":"poc","GATEWAY_API_KEY":"gateway-test",
            "LSK_TENANT_ID":"lsk-synthetic","LSK_ENABLE_DEMO_WRITES":"false",
        }, clear=True)
        self.environ.start()
        self.addCleanup(self.environ.stop)

    def test_unknown_business_domain_fails_closed(self):
        result=self.client.post("/v1/platform/ask",headers=self.headers,json={
            "domain":"unknown","question":"How do finance exceptions work?","use_model":False})
        self.assertEqual(result.status_code,404)

    def test_acl_limits_context_to_requested_domain(self):
        scope=scope_for("employee","finance")
        rows=retrieve("invoice review campaign account",scope)
        self.assertEqual([row["id"] for row in rows],["lsk-invoice-standards-v1"])

    def test_cannot_select_other_tenant(self):
        with patch.dict(os.environ,{"LSK_TENANT_ID":"another-tenant"}):
            self.assertEqual(retrieve("invoice review",scope_for("employee","finance")),[])

    def test_unlisted_actor_sees_no_documents(self):
        self.assertEqual(retrieve("invoice review",scope_for("unlisted-actor","finance")),[])

    def test_retrieval_only_does_not_call_model(self):
        with patch("integrations.enterprise_api.infer",new_callable=AsyncMock) as model:
            r=self.client.post("/v1/platform/ask",headers=self.headers,json={
                "domain":"finance","question":"Explain invoice exception review","use_model":False})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()["mode"],"retrieval-only")
        self.assertEqual(len(r.json()["evidence"]["sources"]),1)
        model.assert_not_awaited()

    def test_missing_model_fails_instead_of_faking_generated_answer(self):
        r=self.client.post("/v1/platform/ask",headers=self.headers,json={
            "domain":"finance","question":"Explain invoice exception review","use_model":True})
        self.assertEqual(r.status_code,503)
        self.assertIn("BEDROCK_MODEL_ID",r.json()["detail"])

    def test_stage_cannot_use_demo_key_as_enterprise_login(self):
        with patch.dict(os.environ,{"LSK_STAGE":"production"}):
            r=self.client.get("/v1/apps",headers=self.headers)
        self.assertEqual(r.status_code,503)

    def test_demo_mutations_are_disabled_by_default(self):
        r=self.client.post("/v1/apps/finance/proposals",headers=self.headers,json={
            "record_id":"inv-1002","text":"Request review","reason":"Synthetic mismatch"})
        self.assertEqual(r.status_code,403)

    def test_same_idempotency_key_replays_without_duplicate_write(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{
            "LSK_COMMAND_DB":str(Path(temp)/"commands.sqlite3"),"LSK_ENABLE_DEMO_WRITES":"true"}):
            payload={"domain":"finance","record_id":"inv-1002","text":"Review invoice","reason":"Mismatch"}
            headers={**self.headers,"Idempotency-Key":"req-0001"}
            first=self.client.post("/v1/platform/proposals",headers=headers,json=payload)
            second=self.client.post("/v1/platform/proposals",headers=headers,json=payload)
            self.assertEqual(first.status_code,201)
            self.assertEqual(second.status_code,201)
            self.assertEqual(first.json()["proposal_id"],second.json()["proposal_id"])
            self.assertFalse(first.json()["replayed"])
            self.assertTrue(second.json()["replayed"])
            self.assertEqual(len(my_proposals("lsk-synthetic","employee")),1)
            different=self.client.post("/v1/platform/proposals",headers=headers,
                                       json={**payload,"text":"Different request"})
            self.assertEqual(different.status_code,409)

    def test_bedrock_mock_is_genuinely_separate_from_retrieval_only(self):
        mock=lambda model,prompt,system: {
            "output":{"message":{"content":[{"text":"Invoice inv-1002 requires review."}]}},
            "usage":{"inputTokens":30,"outputTokens":9}}
        with patch.dict(os.environ,{"BEDROCK_MODEL_ID":"configured-test-model"}):
            result=asyncio.run(infer("Explain the invoice",{"sources":[{"id":"inv-1002"}]},call=mock))
        self.assertEqual(result["mode"],"bedrock-converse")
        self.assertEqual(result["usage"]["input_tokens"],30)
        self.assertEqual(result["actions_taken"],[])

if __name__=="__main__":
    unittest.main()
