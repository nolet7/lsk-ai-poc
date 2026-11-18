"""P28-06 — Authorize, retrieve, infer, verify, respond. Not yet wired to API."""
from __future__ import annotations

async def answer_business_question(*, actor: str, domain: str, question: str,
                                   record_id: str | None = None,
                                   use_model: bool = False) -> dict:
    # TASK P28-06: authorize with existing scope_for before any data fetch.
    # TASK: reuse existing retrieve() and authorized forward() only if justified.
    # TASK: distinguish retrieval-only, abstention, and real Bedrock inference.
    # TASK: ensure model output is grounded in authorized source IDs.
    # TASK: actions_taken MUST remain [] (never execute transactions).
    # TASK: do not expose tracebacks or private service details to users.
    # TASK: add dependency injection or seams for unit tests (mock AWS/business APIs).
    raise NotImplementedError("P28-06: implement governed question workflow")
