"""Offline structural guard: environments remain explicit, safe, and opt-in."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("poc", "pilot", "production")

def main() -> None:
    for stage in STAGES:
        folder = ROOT / "deploy" / "environments" / stage
        assert (folder / "README.md").is_file(), stage
        cfg = json.loads((folder / "config.example.json").read_text(encoding="utf-8"))
        assert cfg["environment"] == stage
        assert cfg["cloud_changes_allowed"] is False, stage
        if stage != "production":
            assert cfg["data_classification"] == "synthetic-only"
            assert cfg["live_inference"] is False and cfg["live_inference_ack"] is False
        else:
            assert cfg["status"] == "infrastructure-implemented-not-deployed"
            assert cfg["required_azs"] >= 2
            assert (folder / "terraform" / "main.tf").is_file()
            assert (folder / "terraform" / "alerts.tf").is_file()
            assert (folder / "ecr" / "main.tf").is_file()
    assert (ROOT / "deploy" / "environments" / "pilot" / "terraform" / "main.tf").is_file()
    assert (ROOT / "phase28" / "production_app.py").is_file()
    assert (ROOT / "phase28" / "sql" / "001_init_postgres.sql").is_file()
    print("PASS: POC/pilot/production infrastructure files, status and fail-closed defaults")

if __name__ == "__main__":
    main()
