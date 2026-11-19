# P28-13: authenticated, read-only FastAPI gateway

## Purpose
The new gateway verifies signed RS256 OIDC access tokens against trusted, operator-provided JWKS, validates issuer, audience, expiry, not-before, issued-at and required identity claims, and converts them into a tenant-scoped Principal. Unauthorized requests never reach retrieval. All gateway requests are retrieval-only. No Bedrock SDK, AWS credentials or business mutation paths are used.

## Install/test
From repository root:
```bash
python -m pip install -r requirements-p28-13.txt
python -m unittest discover -s phase28/tests -p 'test_gateway.py' -v
python -m unittest discover -s phase28/tests -v
```

## Deploy limitations
- The gateway is a dependency-injected app factory; it is intentionally **not** exported as a runnable public `app` with synthetic identities.
- Production composition must obtain an issuer and JWKS from a trusted OIDC configuration/discovery path with HTTPS, controlled refresh and key rotation. Never accept arbitrary JWKS URIs from clients.
- Authorization uses roles from the verified token; provision trusted tenant membership and role assignment in the IdP and storage ACLs.
- `retrieve(scope)` MUST apply tenant and domain filters at the database/vector-search level. A scope check on returned documents alone is not sufficient isolation.
- Audit sink must be durable/available and refuse sensitive payloads. Health route exposes no secrets.
- Keep AI_LIVE_INFERENCE=false. This route rejects `use_model=true` (HTTP 403) even if a token is valid.
- Do not deploy publicly before implementing trusted assembly, TLS ingress, request limits, trusted JWKS refresh, operational monitoring, multi-tenant security assessment and secure audit handling.
