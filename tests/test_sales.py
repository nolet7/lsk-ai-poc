"""Regression tests requiring only the Python standard library for core logic."""
import os
import asyncio
import tempfile
import unittest
from unittest.mock import patch

from sales_enablement import intelligence, store

class SalesWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old_path=store.DB_PATH
        store.DB_PATH=__import__("pathlib").Path(self.temp.name)/"sales.sqlite3"
        store.initialize()

    def tearDown(self):
        store.DB_PATH=self.old_path
        self.temp.cleanup()

    def test_seed_data_and_grounded_brief(self):
        account=store.get_account("acme")
        self.assertEqual(account["name"],"Acme Analytics")
        with patch.dict(os.environ,{"OPENAI_API_KEY":""}):
            brief=asyncio.run(intelligence.account_brief(account))
        self.assertEqual(brief["mode"],"deterministic")
        self.assertTrue(brief["evidence"])
        self.assertEqual(brief["account_id"],"acme")

    def test_changes_require_distinct_reviewer(self):
        before=store.get_account("acme")["notes"]
        proposed=store.request_change("acme","Follow-up confirmed for next Tuesday","Sales owner verified","sales.user")
        self.assertEqual(store.get_account("acme")["notes"],before)
        with self.assertRaises(PermissionError):
            store.decide(proposed["id"],"sales.user",True)
        result=store.decide(proposed["id"],"finance.reviewer",True)
        self.assertEqual(result["status"],"approved")
        self.assertIn("Follow-up confirmed",store.get_account("acme")["notes"])
        with self.assertRaises(ValueError):
            store.decide(proposed["id"],"other.reviewer",True)
        self.assertEqual(len(store.list_events()),2)

    def test_rejection_does_not_modify_crm(self):
        before=store.get_account("northstar")["notes"]
        proposed=store.request_change("northstar","Send revised campaign scope","Requested by buyer","sales.user")
        store.decide(proposed["id"],"marketing.reviewer",False)
        self.assertEqual(store.get_account("northstar")["notes"],before)

    def test_async_model_inference_with_mock_transport(self):
        import json
        import httpx
        account=store.get_account("acme")
        async def handler(request):
            self.assertIn("Bearer",request.headers["Authorization"])
            body=json.loads(request.content)
            self.assertEqual(body["model"],"test-model")
            return httpx.Response(200,json={"choices":[{"message":{"content":json.dumps({"summary":"Acme renewal","risks":["Close date"],"recommended_actions":["Follow up"]})}}]})
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await intelligence.account_brief(account,client=client)
        with patch.dict(os.environ,{"OPENAI_API_KEY":"test-only","SALES_LLM_MODEL":"test-model"}):
            brief=asyncio.run(run())
        self.assertEqual(brief["mode"],"llm")
        self.assertEqual(brief["summary"],"Acme renewal")

    def test_unknown_account_rejected(self):
        with self.assertRaises(KeyError):
            store.request_change("missing","Sample note","Sample reason","sales.user")

if __name__=="__main__":
    unittest.main()
