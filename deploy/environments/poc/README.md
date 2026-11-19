# POC — demonstrate the business workflow

**Purpose:** Validate a business question can be authenticated, authorized against a tenant/domain, matched to scoped records, and either answered with citations or safely refused.

**Existing code:** `phase28/live_app.py`, `phase28/oidc.py`, `phase28/authorization.py`, `phase28/grounding.py`, and `phase28/tests/`.

## Run offline
```bash
python -m pip install -r requirements-p28-13.txt
python -m unittest discover -s phase28/tests -v
python scripts/check_fde_environments.py
```

Model API requests are mocked by tests; **passing tests is not proof of a live Bedrock call**. For a real local API use `phase28.live_app:from_environment` with trusted OIDC JWKS, RBAC, a seeded SQLite DB and explicit environment variables from `deploy/aws/phase28_ec2/ai.env.example`; keep model opt-ins disabled until authorized.

## Acceptance evidence
- Valid token, authorized tenant/document: retrieval-only response with record IDs.
- Missing/invalid token: 401; unauthorized domain: 403.
- Cross-tenant evidence never returned; absent evidence abstains.
- Disabled inference returns 403 on model requests; error handling does not leak credentials.
- Report actual test counts and commit SHA, not invented impact metrics.

**Exit criterion:** reviewable demo and green CI, plus a documented pilot change request.
