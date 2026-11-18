"""P28-07: validate source identifiers against tenant/domain-scoped evidence.

Citation membership is NOT a factual entailment or hallucination check.
"""
from __future__ import annotations

import re

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class GroundingError(ValueError):
    """Evidence or citation validation failed."""


def allowed_source_ids(evidence: dict) -> frozenset[str]:
    if not isinstance(evidence, dict) or not isinstance(evidence.get("sources"), list):
        raise GroundingError("Invalid evidence")
    sources = evidence["sources"]
    if len(sources) > 100:
        raise GroundingError("Too many sources")
    ids: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise GroundingError("Invalid source")
        sid = source.get("id")
        if not isinstance(sid, str) or not _ID.fullmatch(sid) or sid in ids:
            raise GroundingError("Invalid or duplicate source ID")
        ids.add(sid)
    return frozenset(ids)


def validate_grounded_answer(answer: str, cited_source_ids: list[str], evidence: dict) -> dict:
    permitted = allowed_source_ids(evidence)
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 8000:
        raise GroundingError("Invalid answer")
    if not isinstance(cited_source_ids, list) or not cited_source_ids:
        raise GroundingError("Answer must cite at least one source")
    if len(cited_source_ids) > 100 or any(
        not isinstance(i, str) or i not in permitted for i in cited_source_ids
    ) or len(set(cited_source_ids)) != len(cited_source_ids):
        raise GroundingError("Unauthorized or duplicate citation")
    return {"answer": answer.strip(), "cited_source_ids": list(cited_source_ids)}
