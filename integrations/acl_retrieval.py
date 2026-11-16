"""ACL filtering happens BEFORE assembling model context.

Uses a deliberately small local synthetic corpus, not an unrestricted filesystem
or a real tenant-aware vector database. Denies documents without explicit ACLs.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from .enterprise_policy import Scope

def load_corpus() -> list[dict]:
    location = Path(os.getenv("LSK_KNOWLEDGE_FILE", str(Path(__file__).resolve().parent / "synthetic_knowledge.json")))
    if not location.is_file():
        raise RuntimeError("Approved knowledge corpus is unavailable")
    data = json.loads(location.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Invalid corpus")
    return data

def retrieve(question: str, scope: Scope, limit: int = 4) -> list[dict]:
    if not question.strip() or len(question) > 2000 or not 1 <= limit <= 10:
        raise ValueError("Invalid retrieval request")
    words = set(re.findall(r"[a-z0-9]{3,}", question.lower()))
    results = []
    for d in load_corpus():
        if not isinstance(d, dict) or d.get("tenant_id") != scope.tenant:
            continue
        if not isinstance(d.get("id"), str) or not isinstance(d.get("text"), str):
            continue
        if d.get("classification") != "synthetic":
            continue
        if not isinstance(d.get("allowed_subjects"), list) or scope.subject not in d["allowed_subjects"]:
            continue
        if not isinstance(d.get("allowed_domains"), list) or not set(d["allowed_domains"]).intersection(scope.domains):
            continue
        source_words = set(re.findall(r"[a-z0-9]{3,}", (d.get("title", "") + " " + d["text"]).lower()))
        score = len(words & source_words)
        if score:
            results.append((score, {"id": d["id"], "title": d.get("title", d["id"]),
                                    "text": d["text"][:3000], "source": "synthetic-approved-corpus"}))
    results.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [item for _, item in results[:limit]]
