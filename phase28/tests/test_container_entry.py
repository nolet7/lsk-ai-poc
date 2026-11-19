"""P28-14 regression and P28-15 transition away from Docker CI."""
from __future__ import annotations
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from phase28.container_entry import app
ROOT=Path(__file__).resolve().parents[2]
class TestContainerEntry(unittest.TestCase):
    def setUp(self): self.client=TestClient(app)
    def test_liveness_only(self):
        r=self.client.get('/health/live');self.assertEqual(r.status_code,200);self.assertEqual(r.json(),{'status':'alive'})
    def test_readiness_denied_until_wired(self): self.assertEqual(self.client.get('/health/ready').status_code,503)
    def test_business_requests_fail_closed(self):
        self.assertEqual(self.client.post('/v1/business/questions',json={'question':'hello','domain':'orders'}).status_code,503)
    def test_no_openapi_or_docs(self):
        for uri in ('/openapi.json','/docs','/redoc'): self.assertEqual(self.client.get(uri).status_code,404)
    def test_dockerfile_non_root_and_no_fake_credentials(self):
        # Historical P28-14 artifact is deliberately retained but no longer used in CI.
        d=(ROOT/'deploy/aws/phase28_gateway/Dockerfile').read_text()
        self.assertIn('USER 10001:10001',d);self.assertIn('python:3.12-slim',d)
        self.assertNotIn('AWS_ACCESS_KEY_ID=',d);self.assertNotIn('AI_LIVE_INFERENCE=true',d)
        self.assertIn('phase28.container_entry:app',d)
    def test_kubernetes_defaults_to_zero_replicas(self):
        y=(ROOT/'deploy/aws/phase28_gateway/k8s.yaml').read_text()
        for fragment in ('replicas: 0','readOnlyRootFilesystem: true','allowPrivilegeEscalation: false','runAsNonRoot: true','AI_LIVE_INFERENCE'):
            self.assertIn(fragment,y)
    def test_ci_no_cloud_credentials_and_scans_dependencies(self):
        y=(ROOT/'.github/workflows/phase28-p14-ci.yml').read_text()
        self.assertIn('pip-audit',y);self.assertNotIn('docker build',y)
        self.assertIn('python -m unittest discover',y)
        self.assertNotIn('aws-actions/configure-aws-credentials',y)
        self.assertNotIn('docker push',y)
    def test_dockerignore_excludes_sensitive_files(self):
        content=(ROOT/'.dockerignore').read_text()
        for entry in ('**/.env','**/*.tfstate','**/.terraform/','**/.git/'): self.assertIn(entry,content)
if __name__=='__main__': unittest.main()
