import os
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from integrations.gateway import app

class GatewayCommercialTests(unittest.TestCase):
    def setUp(self):
        # Test POC API contracts independently of the checkout's immutable stage.
        self._stage = patch("integrations.gateway.stage", return_value="poc")
        self._metricstage = patch("integrations.observability.stage", return_value="poc")
        self._stage.start()
        self._metricstage.start()
        self.addCleanup(self._stage.stop)
        self.addCleanup(self._metricstage.stop)
        self.client = TestClient(app)
        self.headers = {"X-API-Key":"test-key","X-Actor":"sales.manager"}
    def test_requires_gateway_auth(self):
        with patch.dict(os.environ, {"GATEWAY_API_KEY":"test-key"}):
            r=self.client.post("/v1/agent/run",json={"question":"Find open accounts"})
        self.assertEqual(r.status_code,401)
    def test_validates_question(self):
        with patch.dict(os.environ, {"GATEWAY_API_KEY":"test-key"}):
            r=self.client.post("/v1/agent/run",json={"question":"x"},headers=self.headers)
        self.assertEqual(r.status_code,422)
    def test_default_no_write_permission(self):
        with patch.dict(os.environ, {"GATEWAY_API_KEY":"test-key"}), \
             patch("integrations.gateway.run_commercial_agent",new_callable=AsyncMock) as agent:
            agent.return_value={"answer":"Synthetic sales account summary"}
            r=self.client.post("/v1/agent/run",json={"question":"Summarize accounts"},headers=self.headers)
            self.assertEqual(r.status_code,200)
            self.assertEqual(agent.await_args.kwargs["allow_proposals"],False)
