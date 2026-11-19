# LSK AI — environment-driven FDE delivery

This folder separates **POC**, **pilot**, and **production-style target**. Shared Python source remains in `phase28/`; we do not fork application logic between environments.

| Stage | Runtime | Business integration | Status |
|---|---|---|---|
| POC | Local Python / FastAPI TestClient | Synthetic evidence, fake Bedrock client by default | Code and tests available |
| Pilot | Private Ubuntu EC2 + systemd + SSM | Synthetic scoped records, optional authorized Bedrock Converse | Deployment files exist; **not deployed** |
| Production-style | ECS Fargate + managed database/storage | Authorized enterprise API connectors, OIDC, evaluations | **Design and implementation backlog**, not deployed |

## Promotion rules
1. **POC → Pilot**: offline tests green; cross-tenant denial; model-disabled-by-default; approved model, issuer and RBAC; no secrets in Git.
2. **Pilot → Production-style**: real IAM/OIDC/Bedrock smoke evidence, operator-approved AWS deployment, failure tests, measured costs, immutable release.
3. **Production release**: must also implement and prove multi-AZ runtime, externally consistent state, IAM isolation, audit retention, model budget, rollback and restoration, alarms and SLOs.

## Entry points
- `poc/README.md`: local simulation, development gates.
- `pilot/README.md`: current private EC2 deployment, exact limitations.
- `production/README.md`: ECS Fargate production target with blocker list.
- `../../docs/fde/README.md`: business/technical delivery narrative.
- `../../scripts/check_fde_environments.py`: offline gate for structure and config.

Run: `python scripts/check_fde_environments.py`

**Safety:** Do not paste tokens/keys into config. No automatic AWS provisioning or live model charges are triggered by this reorganization.
