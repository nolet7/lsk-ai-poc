"""P28-03 — Per-request inference guardrails (budget != AWS spending hard cap)."""
from __future__ import annotations


def check_request_budget(question: str, evidence: dict, *, max_chars: int) -> None:
    # TASK P28-03: reject oversized questions/contexts before model invocation.
    # TASK: add a deterministic, configurable upper bound for model output tokens.
    # TASK: discuss request rate limits and concurrency; per-process counters are NOT global.
    raise NotImplementedError("P28-03: implement pre-inference guardrails")


def record_usage(*, model_id: str, input_tokens: int, output_tokens: int) -> dict:
    # TASK P28-03: validate nonnegative usage, return an estimate labelled as estimate.
    # TASK: keep price tables optional/versioned and never confuse budget alerts with caps.
    raise NotImplementedError("P28-03: implement usage accounting")
