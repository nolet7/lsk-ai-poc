"""P28-12 offline smoke checks. No credentials, network, or inference calls."""
from __future__ import annotations

from pathlib import Path
from phase28.config import AISettings


class DeploymentPreflightError(RuntimeError):
    pass


def offline_preflight(*, settings: AISettings, terraform_dir: str | Path) -> dict:
    """Validate offline packaging and fail-closed default configuration."""
    if not isinstance(settings, AISettings):
        raise TypeError("settings must be AISettings")
    if settings.live_inference or settings.live_inference_ack:
        raise DeploymentPreflightError("Offline preflight requires inference disabled")
    root = Path(terraform_dir)
    expected = ("main.tf", "variables.tf", "outputs.tf", "terraform.tfvars.example")
    if not root.is_dir() or any(not (root / f).is_file() for f in expected):
        raise DeploymentPreflightError("Required Terraform files are missing")
    example = (root / "terraform.tfvars.example").read_text(encoding="utf-8")
    if not any(line.strip() == "enabled                       = false" for line in example.splitlines()):
        raise DeploymentPreflightError("The example must disable billable infrastructure")
    return {"status": "offline_preflight_passed", "live_inference": False, "terraform_files": len(expected)}
