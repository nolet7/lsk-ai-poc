"""P28-02 — Validate grounded answers and citations against ACL-filtered evidence."""
from __future__ import annotations


def allowed_source_ids(evidence: dict) -> frozenset[str]:
    # TASK P28-02: extract permitted source IDs from evidence['sources'] after ACL retrieval.
    # TASK: reject malformed evidence and duplicate/conflicting identifiers; never broaden scope.
    raise NotImplementedError("P28-02: implement allowed_source_ids")


def validate_grounded_answer(answer: str, cited_source_ids: list[str], evidence: dict) -> dict:
    # TASK P28-02: ensure citations belong to authorized IDs and answer is nonempty/bounded.
    # TASK: handle no-evidence cases by abstaining rather than fabricating.
    # TASK: do NOT claim that mere ID-validity proves every statement is factually correct.
    raise NotImplementedError("P28-02: implement grounded answer validation")
