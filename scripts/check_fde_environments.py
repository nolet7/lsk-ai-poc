"""Offline structural guard: configs must remain opt-in, honest and isolated."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("poc", "pilot", "production")
def main() -> None:
    for stage in STAGES:
        folder = ROOT / "deploy" / "environments" / stage
        assert (folder / "README.md").is_file(), f"missing documentation: {stage}"
        cfg = json.loads((folder / "config.example.json").read_text(encoding="utf-8"))
        assert cfg["environment"] == stage
        assert cfg["cloud_changes_allowed"] is False, stage
        if stage != "production":
            assert cfg["data_classification"] == "synthetic-only"
            assert cfg["live_inference"] is False
            assert cfg["live_inference_ack"] is False
        else:
            assert cfg["status"] == "design-only"
            assert cfg["required_azs"] >= 2
    assert (ROOT / "deploy/aws/phase28_ec2/main.tf").is_file()
    assert (ROOT / "phase28/live_app.py").is_file()
    print("PASS: POC/pilot/production environment contracts and safe defaults")

if __name__ == "__main__":
    main()
