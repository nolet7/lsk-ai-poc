"""P28-18 offline checks; no AWS, Docker, admin privileges or symlinks."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import unittest
from phase28.supervised_preflight import (verify_record, PreflightRejected,
                                            inspect_checkout, write_evidence)

NOW = datetime(2026, 11, 19, 1, 0, tzinfo=timezone.utc)

def example():
    return {"change_id":"CHG-12345", "operator":"engineer-01",
            "approved_revision":"a"*40, "account_id":"123456789012",
            "region":"us-east-1", "instance_id":"i-0123456789abcdef0",
            "approved_at":(NOW-timedelta(minutes=5)).isoformat(),
            "expires_at":(NOW+timedelta(hours=1)).isoformat(),
            "mode":"diagnostic-only", "operator_confirmed":True}

class TestSupervisedPreflight(unittest.TestCase):
    def test_valid_record(self):
        self.assertEqual(verify_record(example(), now=NOW)["mode"], "diagnostic-only")
    def test_wrong_revision_rejected(self):
        data=example(); data["approved_revision"]="main"
        with self.assertRaises(PreflightRejected): verify_record(data,now=NOW)
    def test_wrong_account_or_instance_rejected(self):
        for field,value in (("account_id","123"),("instance_id","i-xx")):
            with self.subTest(field=field):
                data=example(); data[field]=value
                with self.assertRaises(PreflightRejected): verify_record(data,now=NOW)
    def test_expired_and_future_rejected(self):
        for moment in (NOW+timedelta(days=2),NOW-timedelta(days=2)):
            with self.assertRaises(PreflightRejected): verify_record(example(),now=moment)
    def test_overlong_window_rejected(self):
        data=example();data["expires_at"]=(NOW+timedelta(days=2)).isoformat()
        with self.assertRaises(PreflightRejected): verify_record(data,now=NOW)
    def test_wrong_mode_and_unconfirmed_rejected(self):
        for field,value in (("mode","production"),("operator_confirmed",False)):
            data=example();data[field]=value
            with self.assertRaises(PreflightRejected):verify_record(data,now=NOW)
    def test_unknown_fields_rejected(self):
        data=example();data["aws_secret_access_key"]="never"
        with self.assertRaises(PreflightRejected): verify_record(data,now=NOW)
    def test_untrusted_checkout_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(PreflightRejected):inspect_checkout(Path(d),"a"*40)
    def test_receipt_exclusive_and_no_secret(self):
        with tempfile.TemporaryDirectory() as d:
            data=verify_record(example(),now=NOW)
            output=write_evidence(Path(d),data,now=NOW)
            payload=json.loads(output.read_text())
            self.assertEqual(payload["status"],"record-validated-not-host-authorized")
            self.assertNotIn("operator_confirmed",str(payload))
            with self.assertRaises(PreflightRejected):write_evidence(Path(d),data,now=NOW)
    def test_shell_and_ci_controls_present(self):
        root=Path(__file__).resolve().parents[2]
        script=(root/'deploy/aws/phase28_ec2/host-readonly-preflight.sh').read_text()
        ci=(root/'.github/workflows/phase28-p18-ci.yml').read_text()
        for token in ('systemctl', 'nginx -t', 'ss -lnt', 'flock', '127.0.0.1'):
            self.assertIn(token,script)
        self.assertIn('python -m unittest discover',ci)
        self.assertNotIn('aws-actions/configure-aws-credentials',ci)
        self.assertNotIn('docker build',ci)

if __name__=='__main__':unittest.main()
