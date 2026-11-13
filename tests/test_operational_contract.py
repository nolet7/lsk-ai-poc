import os
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from integrations.gateway import app

class OperationsTests(unittest.TestCase):
    def setUp(self):
        # Test POC API contracts independently of the checkout's immutable stage.
        self._stage = patch("integrations.gateway.stage", return_value="poc")
        self._metricstage = patch("integrations.observability.stage", return_value="poc")
        self._stage.start()
        self._metricstage.start()
        self.addCleanup(self._stage.stop)
        self.addCleanup(self._metricstage.stop)
        self.client=TestClient(app)
        self.headers={"X-API-Key":"test-key","X-Actor":"qa"}

    def test_readiness_requires_auth(self):
        with patch.dict(os.environ, {"GATEWAY_API_KEY":"test-key"}):
            response=self.client.get("/ready")
        self.assertEqual(response.status_code,401)

    def test_readiness_fails_if_model_unconfigured(self):
        with patch.dict(os.environ, {"GATEWAY_API_KEY":"test-key"}, clear=True), \
             patch("integrations.gateway.forward", new_callable=AsyncMock) as forward:
            forward.return_value={"domain":"sales"}
            response=self.client.get("/ready",headers=self.headers)
        self.assertEqual(response.status_code,503)
        self.assertFalse(response.json()["detail"]["bedrock_model_configured"])

    def test_readiness_only_checks_config_and_services(self):
        with patch.dict(os.environ, {"GATEWAY_API_KEY":"test-key","BEDROCK_MODEL_ID":"test-model"}, clear=True), \
             patch("integrations.gateway.forward", new_callable=AsyncMock) as forward:
            forward.return_value={"domain":"sales"}
            response=self.client.get("/ready",headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(forward.await_count,3)
        self.assertIn("not verified",response.json()["note"])

    def test_agent_portal_is_static_and_read_only(self):
        response=self.client.get("/agent")
        self.assertEqual(response.status_code,200)
        self.assertIn("Commercial AI Assistant", response.text)
        self.assertIn("allow_proposals:false", response.text)

    def test_pilot_metrics_require_dedicated_key(self):
        with patch.dict(os.environ, {"LSK_STAGE":"pilot","METRICS_API_KEY":"metrics-secret"}, clear=True), \
             patch("integrations.observability.stage",return_value="pilot"):
            denied=self.client.get("/internal/metrics")
            allowed=self.client.get("/internal/metrics",headers={"X-Metrics-Key":"metrics-secret"})
        self.assertEqual(denied.status_code,401)
        self.assertEqual(allowed.status_code,200)

    def test_metrics_do_not_require_customer_credentials(self):
        response=self.client.get("/internal/metrics")
        self.assertEqual(response.status_code,200)
        self.assertIn("lsk_gateway_requests_total",response.text)
