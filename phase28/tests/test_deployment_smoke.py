"""P28-12 offline acceptance tests; no AWS calls."""
import tempfile
import unittest
from pathlib import Path
from phase28.config import AISettings
from phase28.deployment_smoke import DeploymentPreflightError, offline_preflight

ROOT = Path(__file__).resolve().parents[2] / "deploy" / "aws" / "phase28_poc"

class TestDeploymentSmoke(unittest.TestCase):
    def test_default_preflight(self):
        result = offline_preflight(settings=AISettings(), terraform_dir=ROOT)
        self.assertEqual(result["status"], "offline_preflight_passed")
        self.assertFalse(result["live_inference"])

    def test_live_flag_rejected(self):
        with self.assertRaises(DeploymentPreflightError):
            offline_preflight(settings=AISettings(live_inference=True, live_inference_ack=True), terraform_dir=ROOT)

    def test_missing_manifests_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DeploymentPreflightError):
                offline_preflight(settings=AISettings(), terraform_dir=tmp)

    def test_no_network_or_aws_imports_in_preflight(self):
        text = (Path(__file__).resolve().parents[1] / "deployment_smoke.py").read_text()
        self.assertNotIn("import boto3", text)
        self.assertNotIn("socket", text)

    def test_example_disables_resources(self):
        source = (ROOT / "terraform.tfvars.example").read_text()
        self.assertIn("enabled                       = false", source)

if __name__ == "__main__":
    unittest.main()
