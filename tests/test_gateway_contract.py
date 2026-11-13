import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from integrations.gateway import app

class GatewayContractTests(unittest.TestCase):
    def setUp(self):
        self._stage=patch("integrations.gateway.stage",return_value="poc")
        self._metricstage=patch("integrations.observability.stage",return_value="poc")
        self._stage.start()
        self._metricstage.start()
        self.addCleanup(self._stage.stop)
        self.addCleanup(self._metricstage.stop)
        self.client=TestClient(app)
        self.headers={"X-API-Key":"test-gateway-key","X-Actor":"employee"}
    def test_health(self):
        res=self.client.get("/health")
        self.assertEqual(res.status_code,200)
        self.assertEqual(set(res.json()["services"]),{"sales","marketing","finance"})
    def test_rejects_missing_auth(self):
        with patch.dict(os.environ,{"GATEWAY_API_KEY":"test-gateway-key"}):
            res=self.client.get("/v1/apps")
        self.assertEqual(res.status_code,401)
    def test_unknown_domain_rejected(self):
        with patch.dict(os.environ,{"GATEWAY_API_KEY":"test-gateway-key","DEMO_API_KEY":"service-key"}):
            res=self.client.get("/v1/apps/unknown/records",headers=self.headers)
        self.assertEqual(res.status_code,404)
    def test_reviewer_role_required(self):
        with patch.dict(os.environ,{"GATEWAY_API_KEY":"test-gateway-key","DEMO_API_KEY":"service-key"}):
            res=self.client.post("/v1/apps/sales/proposals/example/decision",json={"approve":True},headers=self.headers)
        self.assertEqual(res.status_code,403)

if __name__=="__main__":
    unittest.main()
