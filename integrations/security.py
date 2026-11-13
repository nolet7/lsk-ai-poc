"""Verified JWT identity for the pilot/production gateway.

POC uses a demo shared key. Pilot/production reject demo headers entirely and
require a signature-verified OIDC access token with issuer, audience and roles.
The caller identity is always derived from the validated JWT's 'sub' claim.
"""
from __future__ import annotations

import os
import urllib.parse
from dataclasses import dataclass
from functools import lru_cache
from fastapi import HTTPException


@dataclass(frozen=True)
class Principal:
    subject: str
    domains: frozenset[str]
    roles: frozenset[str]
    mode: str = "oidc"


def stage() -> str:
    value = os.getenv("LSK_STAGE", "poc").lower()
    if value not in ("poc", "pilot", "production"):
        raise HTTPException(status_code=503, detail="Invalid release stage")
    return value


@lru_cache(maxsize=8)
def _jwks_client(uri: str):
    from jwt import PyJWKClient
    return PyJWKClient(uri, cache_keys=True, lifespan=300, timeout=5)


def verify_oidc_token(token: str) -> Principal:
    """Validate signature, registered claims and configured least-privilege roles.

    JWKS host is restricted to the configured issuer host; arbitrary URL values
    supplied by callers are never used.
    """
    issuer = os.getenv("OIDC_ISSUER", "").rstrip("/")
    audience = os.getenv("OIDC_AUDIENCE", "")
    jwks_uri = os.getenv("OIDC_JWKS_URL", "")
    if not issuer or not audience or not jwks_uri:
        raise HTTPException(status_code=503, detail="OIDC configuration is incomplete")
    i = urllib.parse.urlparse(issuer)
    j = urllib.parse.urlparse(jwks_uri)
    if (i.scheme != "https" or j.scheme != "https" or not i.hostname or
            i.hostname != j.hostname or i.port != j.port or j.username or j.password):
        raise HTTPException(status_code=503, detail="OIDC issuer/JWKS URL configuration is unsafe")
    try:
        import jwt
        signing_key = _jwks_client(jwks_uri).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, signing_key.key, algorithms=["RS256"], audience=audience,
            issuer=issuer, options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            leeway=30,
        )
        sub = claims["sub"]
        if not isinstance(sub, str) or not 1 <= len(sub) <= 128:
            raise ValueError("Invalid subject")
        roles = claims.get("roles", [])
        domains = claims.get("domains", [])
        if isinstance(roles, str):
            roles = roles.split()
        if not isinstance(roles, list) or not all(isinstance(v, str) for v in roles):
            raise ValueError("Invalid roles")
        if not isinstance(domains, list) or not all(isinstance(v, str) for v in domains):
            raise ValueError("Invalid domains")
        permitted = frozenset(domains).intersection({"sales", "marketing", "finance"})
        if not permitted or "lsk.ai.read" not in roles:
            raise HTTPException(status_code=403, detail="AI platform access is not authorized")
        return Principal(subject=sub, domains=permitted, roles=frozenset(roles))
    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError, Exception) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired OIDC token") from exc


def ensure_domain(principal: Principal | str, domain: str) -> None:
    if isinstance(principal, Principal) and domain not in principal.domains:
        raise HTTPException(status_code=403, detail="Access to this business domain is denied")


def ensure_reviewer(principal: Principal | str) -> None:
    if not isinstance(principal, Principal) or "lsk.ai.reviewer" not in principal.roles:
        raise HTTPException(status_code=403, detail="Verified reviewer role required")
