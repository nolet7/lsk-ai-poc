"""P28-01 — Safe Bedrock configuration. Do not call AWS when importing this module."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class AISettings:
    # TASK P28-01: define env-driven approved model ID and AWS region, input/output limits,
    # allowed POC stage, timeouts, and explicit inference opt-in.
    # TASK: validate untrusted env values and reject missing or invalid mandatory settings.
    # TASK: never accept AWS credentials or model ID from a browser request.
    pass

def load_settings() -> AISettings:
    # TASK P28-01: implement. Do not introduce a fallback that silently calls a model.
    raise NotImplementedError("P28-01: implement settings validation")
