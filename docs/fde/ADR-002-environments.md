# ADR-002: Separate POC, pilot and production-style delivery

**Status:** Accepted as repository organization; production implementation pending.

## Decision
Keep one Python application source under `phase28/` and create environment-specific deployment contracts under `deploy/environments/`. Preserve the existing `deploy/aws/phase28_ec2/` code as the *pilot* path. Build a separate ECS Fargate production implementation only when the migration requirements and approvals are met.

## Why
The single-host EC2 deployment is useful for integration and SSM operational practice but cannot honestly support multi-AZ availability, distributed quotas, safe horizontal scaling or reliable production storage. Treating it as production would blur tested and untested claims.

## Consequences
- POC: low operational cost, mocked/controlled model, synthetic evidence.
- Pilot: live but intentionally restricted AWS service. Cloud costs and secrets must be approved.
- Production: containerization and managed durable storage require further engineering.
- Promotion must be evidence-driven; no environment is declared production by directory name.

## Alternative considered
Deploy all three stages on EC2. Rejected as default because host management and single-instance SQLite introduce unnecessary production risk. EKS remains an option when organizational Kubernetes standards require it.
