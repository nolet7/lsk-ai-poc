"""Hard boundaries for the LSK synthetic commercial AI platform.

The existing X-API-Key/X-Actor interface is POC identity, NOT enterprise SSO.
Tenant is server-defined; clients may not select an arbitrary tenant.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from fastapi import HTTPException

DOMAINS = frozenset({"sales", "marketing", "finance"})

@dataclass(frozen=True)
class Scope:
    tenant: str
    subject: str
    domains: frozenset[str]
    stage: str

def scope_for(actor: str, domain: str | None = None) -> Scope:
    stage = os.getenv("LSK_STAGE", "poc").lower()
    if stage not in ("poc", "pilot", "production"):
        raise HTTPException(503, "Unknown deployment stage")
    # POC is intentionally single-tenant. A real multi-tenant design requires
    # cryptographically verified tenant and per-record grants from the IdP.
    if stage != "poc":
        raise HTTPException(503, "Enterprise OIDC authorization is not configured on the main POC gateway")
    tenant = os.getenv("LSK_TENANT_ID", "lsk-synthetic")
    if not tenant or len(tenant) > 80 or "/" in tenant:
        raise HTTPException(503, "Invalid server tenant")
    if domain is not None and domain not in DOMAINS:
        raise HTTPException(404, "Unknown business domain")
    return Scope(tenant, actor, DOMAINS, stage)

def require_demo_proposals() -> None:
    if os.getenv("LSK_STAGE", "poc").lower() != "poc" or os.getenv("LSK_ENABLE_DEMO_WRITES", "").lower() != "true":
        raise HTTPException(403, "Demo write capability disabled; isolated synthetic POC opt-in required")
