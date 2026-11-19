"""P28-13: authenticated retrieval-only gateway, no Bedrock or business writes."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from phase28.authorization import AccessDenied, DomainAuthorizer
from phase28.oidc import OIDCVerifier, AuthenticationFailed
from phase28.service import ServiceError, answer_business_question


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=4000)
    record_id: str | None = Field(default=None, min_length=1, max_length=128)
    use_model: bool = False


def create_app(*, verifier: OIDCVerifier, authorizer: DomainAuthorizer,
               retrieve: Callable, audit_sink: Callable) -> FastAPI:
    if not isinstance(verifier, OIDCVerifier) or not isinstance(authorizer, DomainAuthorizer):
        raise TypeError("Verified OIDC configuration and role policy required")
    if not callable(retrieve) or not callable(audit_sink):
        raise TypeError("Trusted retrieval and audit dependencies required")
    app = FastAPI(title="LSK Phase 28 Read-only AI Gateway", version="0.13.0")

    @app.get("/health/live")
    async def liveness() -> dict:
        return {"status": "alive"}  # No inference, credentials or DB access.

    @app.post("/v1/business/questions")
    async def ask(payload: QuestionRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        # This phase forbids even entering a model path, regardless of token scope.
        if payload.use_model is not False:
            raise HTTPException(status_code=403, detail="Model inference disabled")
        if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Bearer"})
        token = authorization[7:]
        if not token or " " in token:
            raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Bearer"})
        try:
            principal = verifier.verify(token)
        except AuthenticationFailed:
            raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Bearer"}) from None
        try:
            return await answer_business_question(
                actor=principal.subject, domain=payload.domain, question=payload.question,
                record_id=payload.record_id, use_model=False,
                principal=principal, authorizer=authorizer, retrieve=retrieve,
                generate=None, audit_sink=audit_sink,
            )
        except AccessDenied:
            raise HTTPException(status_code=403, detail="Forbidden") from None
        except (ServiceError, ValueError, TypeError):
            raise HTTPException(status_code=503, detail="Request unavailable") from None

    return app
