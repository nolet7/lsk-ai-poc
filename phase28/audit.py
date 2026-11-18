"""P28-05 — Structured, privacy-preserving audit event for model requests."""
from __future__ import annotations


def audit_event(*, request_id: str, actor: str, domain: str, outcome: str,
                source_ids: list[str], model_id: str | None = None) -> dict:
    # TASK P28-05: emit an event with safe IDs, stage, timestamps, model usage metadata.
    # TASK: never log gateway keys, AWS credentials, raw questions or full evidence.
    # TASK: clarify that local logs are a POC trail, not tamper-proof audit storage.
    raise NotImplementedError("P28-05: implement sanitized audit record")
