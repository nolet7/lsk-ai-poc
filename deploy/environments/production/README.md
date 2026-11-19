# Production-style target — ECS Fargate

**Status: design / implementation backlog, NOT deployed or production-ready.**

For ASR-style internal enterprise workloads, select ECS Fargate as the default proposed app compute (not EC2). Kubernetes/EKS is an alternative only when cluster-level portability or policies justify its added complexity. This folder intentionally does **not** contain misleading nonfunctional Terraform claiming to be a deployment.

## Target request path
Employee / enterprise client → approved private entry point / API Gateway + VPC Link / private ALB as appropriate → ECS Fargate FastAPI tasks (multi-AZ) → OIDC/JWKS verification + tenant RBAC → authorized evidence service → Bedrock Converse via private interface endpoint → grounded answer + citations → external audit and metrics.

Enterprise ERP/CRM integrations require explicit scoped API identities, read-only defaults, approval on writes, idempotency and tracing.

## Implementation work (required before an AWS production claim)
- [ ] Containerize and pin Python dependencies; scan/sign immutable images in ECR and generate SBOM.
- [ ] Terraform network, endpoint policies, ECS cluster, task/execution roles, task definitions, target group/ALB, secrets, log groups, autoscaling, DNS and certificates.
- [ ] Separate dev/pilot/prod AWS accounts or equivalent rigorously reviewed isolation and encrypted remote Terraform state.
- [ ] Replace SQLite (records, audit and rate limiting) with durable multi-task storage; define migrations, backups and restore targets.
- [ ] Implement central distributed model/token/USD budget, per-tenant quotas, timeouts and fallback/abstention.
- [ ] Configure trusted rotating OIDC JWKS with restrictive egress and fine-grained RBAC/ABAC; negative tenant boundary tests.
- [ ] Add authorized enterprise API adapters and document ACL-aware retrieval; treat retrieved content as untrusted.
- [ ] CI/CD promotion with approvals, canary/rolling deploy, smoke tests, alarms and automatic/manual rollback.
- [ ] OTEL traces, operational dashboards, SLOs/error budgets, Bedrock evals and adversarial security tests.
- [ ] Execute two-AZ failover, load tests, incident drills and DB restore; retain measured evidence.

## Acceptance gates
See `docs/fde/RELEASE_GATES.md`. **No production label** without completed evidence and sign-off.

Do not reuse pilot OIDC files, local SQLite, or single-host request caps as production controls.
