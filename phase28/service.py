"""P28-07: governed retrieval-only / mocked inference application service.

No authentication, AWS client, or business mutation occurs here. Trusted
Principal must be constructed by a verified gateway, not from client text.
The caller supplies tenant-filtered retrieval and an optional budget-governed
model callback; this lab does NOT prove production gateway integration.
"""
from __future__ import annotations

import inspect
from collections.abc import Callable
from uuid import uuid4

from phase28.authorization import AccessDenied, DocumentScope, DomainAuthorizer, Principal
from phase28.audit import audit_event
from phase28.grounding import GroundingError, allowed_source_ids, validate_grounded_answer


class ServiceError(RuntimeError):
    """Safe error for API boundary mapping; no internal details."""


async def _call(fn: Callable, *args):
    value = fn(*args)
    if inspect.isawaitable(value):
        return await value
    return value


async def answer_business_question(
    *, actor: str, domain: str, question: str,
    record_id: str | None = None, use_model: bool = False,
    principal: Principal | None = None,
    authorizer: DomainAuthorizer | None = None,
    retrieve: Callable | None = None,
    generate: Callable | None = None,
    audit_sink: Callable | None = None,
) -> dict:
    """Return read-only answer with allowed citation IDs and sanitized audit.

    `actor` is retained for legacy signature compatibility but is NOT proof of
    identity. `retrieve(scope)` must independently enforce tenant/domain in
    its storage query. `generate(question, evidence)` must be a governed mock
    or budget-controlled inference dependency; no model is created here.
    """
    request_id = uuid4().hex
    # Never derive Principal from caller-supplied actor/tenant strings.
    if not isinstance(principal, Principal) or not isinstance(authorizer, DomainAuthorizer):
        raise AccessDenied("Access denied")
    if actor != principal.subject:
        raise AccessDenied("Access denied")
    if not isinstance(domain, str) or not domain or not isinstance(question, str) or not question.strip():
        raise ValueError("Invalid request")
    if record_id is not None and (not isinstance(record_id, str) or not record_id):
        raise ValueError("Invalid record ID")
    if not callable(retrieve):
        raise TypeError("retrieve dependency required")
    if type(use_model) is not bool:
        raise ValueError("Invalid use_model")

    scope = DocumentScope(principal.tenant_id, domain)

    def event(outcome, ids=()):
        return audit_event(
            request_id=request_id, actor=principal.subject,
            tenant_id=principal.tenant_id, domain=domain,
            outcome=outcome, source_ids=list(ids),
        )

    async def log(outcome, ids=()):
        if audit_sink is not None:
            # If auditing fails, do not return a potentially sensitive response.
            await _call(audit_sink, event(outcome, ids))

    try:
        authorizer.authorize(principal, scope)
    except AccessDenied:
        await log("deny")
        raise

    # Explicitly no data access before authorization; retrieval must also
    # independently enforce SQL/vector-index tenant AND domain filters.
    try:
        evidence = await _call(retrieve, scope)
        ids = allowed_source_ids(evidence)
        for source in evidence["sources"]:
            if source.get("tenant_id") != scope.tenant_id or source.get("domain") != scope.domain:
                raise GroundingError("Out-of-scope evidence")
        if record_id is not None:
            evidence = {
                "sources": [s for s in evidence["sources"] if s.get("record_id") == record_id]
            }
            ids = allowed_source_ids(evidence)
        if not ids:
            await log("abstain")
            return {
                "request_id": request_id, "status": "abstain",
                "answer": "No authorized evidence available.",
                "cited_source_ids": [], "actions_taken": [],
            }
        if not use_model:
            await log("success", ids)
            return {
                "request_id": request_id, "status": "retrieval_only",
                "answer": None, "cited_source_ids": sorted(ids),
                "actions_taken": [],
            }
        if not callable(generate):
            raise ServiceError("Model path unavailable")
        payload = await _call(generate, question, evidence)
        if not isinstance(payload, dict):
            raise GroundingError("Invalid generation")
        grounded = validate_grounded_answer(
            payload.get("answer"), payload.get("cited_source_ids"), evidence
        )
        await log("success", grounded["cited_source_ids"])
        return {
            "request_id": request_id, "status": "answered",
            **grounded, "actions_taken": [],
        }
    except (AccessDenied, GroundingError, ServiceError):
        await log("error")
        raise ServiceError("Request could not be completed") from None
    except Exception:
        await log("error")
        raise ServiceError("Request could not be completed") from None
