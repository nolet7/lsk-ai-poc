import os
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from integrations.gateway import app

class GatewayAIContractTests(unittest.TestCase):
    def setUp(self):
        # Test POC API contracts independently of the checkout's immutable stage.
        self._stage = patch("integrations.gateway.stage", return_value="poc")
        self._metricstage = patch("integrations.observability.stage", return_value="poc")
        self._stage.start()
        self._metricstage.start()
        self.addCleanup(self._stage.stop)
        self.addCleanup(self._metricstage.stop)
        self.client = TestClient(app)
        self.headers = {"X-API-Key":"gateway-test", "X-Actor":"analyst"}
        self.payload = {"domain":"finance", "record_id":"inv1", "question":"Explain the exception"}

    def test_ai_requires_identity(self):
        with patch.dict(os.environ, {"GATEWAY_API_KEY":"gateway-test"}):
            response=self.client.post("/v1/ai/analyze",json=self.payload)
        self.assertEqual(response.status_code,401)

    def test_ai_rejects_unknown_business_domain(self):
        with patch.dict(os.environ, {"GATEWAY_API_KEY":"gateway-test"}):
            response=self.client.post("/v1/ai/analyze",headers=self.headers,json={**self.payload,"domain":"unlisted"})
        self.assertEqual(response.status_code,404)

    def test_ai_returns_actual_model_result_without_write(self):
        explanation={"mode":"bedrock-llm","model":"demo-model","answer":"Reconcile mismatch", "actions_taken":[]}
        with patch.dict(os.environ, {"GATEWAY_API_KEY":"gateway-test"}), \
             patch("integrations.gateway.forward", new_callable=AsyncMock) as forward, \
             patch("integrations.gateway.analyze_with_bedrock",new_callable=AsyncMock) as model:
            forward.return_value={"summary":"Mismatch","signals":{"matched":False}}
            model.return_value=explanation
            response=self.client.post("/v1/ai/analyze",headers=self.headers,json=self.payload)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json(),explanation)
            self.assertEqual(forward.await_count,1)
            model.assert_awaited_once()

    def test_unconfigured_model_returns_503(self):
        from integrations.bedrock_ai import ModelUnavailable
        with patch.dict(os.environ, {"GATEWAY_API_KEY":"gateway-test"}), \
             patch("integrations.gateway.forward",new_callable=AsyncMock) as forward, \
             patch("integrations.gateway.analyze_with_bedrock",new_callable=AsyncMock) as model:
            forward.return_value={"summary":"Mismatch","signals":{}}
            model.side_effect=ModelUnavailable("BEDROCK_MODEL_ID is not configured")
            response=self.client.post("/v1/ai/analyze",headers=self.headers,json=self.payload)
        self.assertEqual(response.status_code,503)
