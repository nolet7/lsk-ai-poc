"""P28-15 offline deployment controls: no AWS, Docker, sudo or network."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "deploy/aws/phase28_ec2"

class EC2DeploymentTests(unittest.TestCase):
    def read(self, path):
        return (BASE / path).read_text(encoding="utf-8")

    def test_disabled_by_default(self):
        self.assertRegex(self.read('variables.tf'), r'variable\s+"enabled"\s*\{[^}]*\bdefault\s*=\s*false\b')
        self.assertIn('enabled = false', self.read('terraform.tfvars.example'))
        self.assertIn('count                       = var.enabled ? 1 : 0', self.read('main.tf'))

    def test_no_public_ip_or_inbound(self):
        tf = self.read('main.tf')
        self.assertIn('associate_public_ip_address = false', tf)
        self.assertNotIn('aws_vpc_security_group_ingress_rule', tf)
        self.assertNotIn('aws_eip', tf)

    def test_imdsv2_encrypted_disk_and_existing_profile(self):
        tf = self.read('main.tf')
        for fragment in ('http_tokens                 = "required"', 'encrypted   = true',
                         'iam_instance_profile        = var.existing_instance_profile_name'):
            self.assertIn(fragment, tf)

    def test_systemd_nonroot_loopback_and_disabled_ai(self):
        unit = self.read('lsk-phase28.service')
        for fragment in ('User=lskphase28', '127.0.0.1', 'ProtectSystem=strict',
                         'AI_LIVE_INFERENCE=false', 'AI_LIVE_INFERENCE_ACK=false',
                         'phase28.container_entry:app'):
            self.assertIn(fragment, unit)

    def test_nginx_loopback_and_closed_business_path(self):
        cfg = self.read('nginx-diagnostic.conf')
        self.assertIn('listen 127.0.0.1:18080',cfg)
        self.assertIn('location / { return 503; }',cfg)
        self.assertNotIn('listen 0.0.0.0',cfg)

    def test_install_manual_and_no_fake_auth(self):
        script=self.read('install-from-checkout.sh')
        self.assertIn('nginx -t',script)
        self.assertIn('systemctl enable --now',script)
        self.assertNotIn('AWS_ACCESS_KEY_ID=',script)
        self.assertNotIn('curl | bash',script)

    def test_dockerless_ci(self):
        cfg=(ROOT/'.github/workflows/phase28-p14-ci.yml').read_text()
        self.assertNotIn('docker build',cfg)
        self.assertNotIn('docker run',cfg)
        self.assertNotIn('configure-aws-credentials',cfg)
        self.assertIn('pip_audit',cfg)

    def test_script_includes_503_smoke(self):
        smoke=self.read('smoke.sh')
        self.assertIn('ex.code == 503',smoke)
        self.assertIn('/health/live',smoke)

if __name__=='__main__':
    unittest.main()
