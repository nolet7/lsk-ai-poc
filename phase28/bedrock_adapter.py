"""P28-04 — Testable real Bedrock inference boundary. No fake AI answers."""
from __future__ import annotations
from collections.abc import Callable

async def generate_answer(question: str, evidence: dict, *, call: Callable | None = None) -> dict:
    # TASK P28-04: reuse integrations.bedrock_gateway.infer(), passing injected mock call
    # in unit tests. Preserve its explicit ModelUnavailable failure contract.
    # TASK: enforce config/budget checks BEFORE invoking Bedrock.
    # TASK: enforce metadata limitations and reject malformed response payloads.
    # TASK: do not catch all errors then return hardcoded AI-looking text.
    raise NotImplementedError("P28-04: implement a Bedrock adapter")
