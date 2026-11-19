# FDE release evidence and go/no-go gates

Mark a gate **PASS only with observed evidence**. Source code or Terraform definitions are not a live deployment.

| Gate | POC | Pilot | Production-style | Evidence |
|---|---|---|---|---|
| Reviewed source SHA and release artifact digest | Required | Required | Required | commit, ECR digest |
| Offline unit, integration and security regression | Required | Required | Required | CI and signed test reports |
| OIDC, RBAC and tenant-isolation negative tests | Required | Required | Required | sanitized 401/403 responses |
| Source citation / no-evidence abstention | Required | Required | Required | sanitized prompt / citation |
| Real Bedrock invocation | Optional | Required | Required | allowed model + region and request record |
| Approved IAM, endpoint, VPC and state access | N/A | Required | Required | plan and IAM role review |
| Enforced token/USD budget and SLO alert drills | Design | Measure | Implement and test | metrics and alarms |
| Rollback, upgrade, DB restore and AZ failover | Plan | Exercise | Execute | restore / chaos reports |
| Production DB least-privilege + managed secret/key rotation | N/A | N/A | Required | role/rotation test |
| Authorized enterprise business API connectors | Synthetic | Approved simulation | Required if in scope | owner approvals / API contracts |
| Business owner and security approval | Local | Pilot | Enterprise release | signed change log |

## Current verified engineering evidence
- GitHub branch: `feature/phase28-ai-deploy`, repository `nolet7/lsk-ai-poc`.
- Previous local offline suite: 174 passed, 10 skipped (supplied by project owner, not rerun here).
- Existing Phase28 regression CI was green after infrastructure changes.
- `fde-aws-infrastructure-validation` verified Terraform validation for pilot, production ECR and production runtime stacks.
- Production-style ECR, ECS, RDS, private endpoints and CloudWatch **exist as code only**.
- Real EC2 install, real OIDC, Bedrock calls, ECR image publishing and ECS/RDS cloud plans/applies **not yet evidenced**.

## Production deployment blockers remaining
- Create reviewed non-master DB user and dedicated migration/admin process.
- Distribute and verify a trusted RDS CA bundle for TLS `verify-full`.
- Implement and test rotating JWKS, model USD/token budgets and immutable audit export.
- Configure protected GitHub publishing environment, approved OIDC provider and scoped deployment identity.
- Run live change-reviewed `terraform plan`, migrations, smoke tests, alarms, cost review and rollback/drills.

This repository simulates an ASR-like commercial environment. It must not be represented as an actual ASR deployment.
