# Production branch — preserved hardening baseline

This branch was created from the earlier `production-hardening` development branch **to retain its distinct implementation** (Docker, CI, evaluations, monitoring, security and application changes). It is not assumed to contain the later Sales POC implementation and is not proof of production deployment.

## CTO decision

Preserve the hardening baseline; validate and integrate Sales workflow changes through reviewed pull requests after pilot acceptance. Do not force-overwrite the production branch with the POC branch or delete unique hardening commits.

## Production readiness criteria

- Authenticated SSO and verified authorization on every business data access and action
- Managed secrets, least-privilege enterprise API connectors, tenant isolation
- Persistent workflow checkpoints, bounded retries, idempotency, auditable approval state
- Security tests, prompt-injection evaluations, regression and load tests
- Documented SLOs, telemetry dashboards, alerts, incident procedures and rollback
- CI-enforced release promotion from pilot with named engineering and business sign-off
- Evidence of measured value on approved non-confidential pilot data

The branch name denotes intended release stage only. Do not deploy publicly or claim production operation without passing these gates.

See `docs/CTO_MANDATE.md`.
