"""Security regression: demo writes stay OFF unless deliberately enabled in POC."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from integrations.gateway import app

class DemoReleaseGuardTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
        self.headers={"X-API-Key":"test-gateway", "X-Actor":"test.employee"}
        self.payload={"record_id":"inv-1002","text":"Review invoice","reason":"Finance exception"}

    def test_default_proposal_denied_without_upstream_call(self):
        with patch.dict(os.environ,{"GATEWAY_API_KEY":"test-gateway","DEMO_API_KEY":"test-service"},clear=True):
            r=self.client.post("/v1/apps/finance/proposals",headers=self.headers,json=self.payload)
        self.assertEqual(r.status_code,403)

    def test_setting_flag_without_poc_stage_not_enough(self):
        with patch.dict(os.environ,{"GATEWAY_API_KEY":"test-gateway","LSK_STAGE":"production","LSK_ENABLE_DEMO_WRITES":"true"},clear=True):
            r=self.client.post("/v1/apps/finance/proposals",headers=self.headers,json=self.payload)
        self.assertEqual(r.status_code,403)

    def test_review_endpoint_stays_denied_in_pilot(self):
        headers={**self.headers,"X-Role":"reviewer"}
        with patch.dict(os.environ,{"GATEWAY_API_KEY":"test-gateway","LSK_STAGE":"pilot","LSK_ENABLE_DEMO_WRITES":"true"},clear=True):
            r=self.client.post("/v1/apps/finance/proposals/example/decision",headers=headers,json={"approve":True})
        self.assertEqual(r.status_code,403)

    def test_ai_write_feature_stays_denied_in_production(self):
        with patch.dict(os.environ,{"GATEWAY_API_KEY":"test-gateway","LSK_STAGE":"production","LSK_ENABLE_DEMO_WRITES":"true"},clear=True):
            r=self.client.post("/v1/agent/run",headers=self.headers,json={"question":"Create a finance note","allow_proposals":True})
        self.assertEqual(r.status_code,403)
