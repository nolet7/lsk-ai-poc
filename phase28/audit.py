"""P28-06: privacy-minimizing audit events for access and AI decisions.

Returned records must be written to an append-only protected sink by the caller.
The dictionary by itself is NOT a durable/tamper-proof audit trail.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_OUTCOMES = frozenset({"allow", "deny", "abstain", "error", "success"})


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"Invalid {name}")
    return value


def audit_event(
    *, request_id: str, actor: str, domain: str, outcome: str,
    source_ids: list[str], model_id: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    """Create an allowlisted event, without prompts or sensitive payloads."""
    _id(request_id, "request_id")
    _id(actor, "actor")
    _id(domain, "domain")
    if tenant_id is not None:
        _id(tenant_id, "tenant_id")
    if outcome not in _OUTCOMES:
        raise ValueError("Invalid audit outcome")
    if not isinstance(source_ids, list) or len(source_ids) > 100:
        raise ValueError("Invalid source identifiers")
    for value in source_ids:
        _id(value, "source_id")
    if model_id is not None:
        _id(model_id, "model_id")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "actor": actor,
        "tenant_id": tenant_id,
        "domain": domain,
        "outcome": outcome,
        "source_ids": list(source_ids),
        "model_id": model_id,
    }
