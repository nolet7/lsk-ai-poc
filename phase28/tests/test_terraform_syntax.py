"""P28-15 regression: reject the invalid inline HCL syntax that broke init.

If Terraform is installed, run its actual formatter parser; it catches more
issues than this minimal fail-fast guard. No AWS requests are made.
"""
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
TF = ROOT / "deploy" / "aws" / "phase28_ec2"


class TerraformSyntaxTests(unittest.TestCase):
    def test_no_semicolon_separated_block_arguments(self):
        for name in ("main.tf", "variables.tf", "outputs.tf"):
            data = (TF / name).read_text(encoding="utf-8")
            with self.subTest(filename=name):
                self.assertNotRegex(data, r'(?m)^\s*(?:variable|output|provider)\s+[^\n]+\{[^\n]*;')
                self.assertNotIn("; default =", data)
                self.assertNotIn("; version =", data)

    @unittest.skipUnless(shutil.which("terraform"), "Terraform CLI not installed")
    def test_terraform_native_syntax_and_format(self):
        result = subprocess.run(
            ["terraform", "fmt", "-check", "-recursive"], cwd=TF,
            text=True, capture_output=True, check=False, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
