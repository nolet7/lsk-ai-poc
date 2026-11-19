# Production-style AWS environment — infrastructure implemented, live validation pending

**Not an ASR Group deployment.** These resources are a proposed LSK enterprise simulation and are **not deployed**. IaC code does not equal production certification.

## Components
- Immutable ECR-image ECS Fargate tasks, multi-AZ service, internal ALB, target health checks, circuit-breaker rollback and CPU-based autoscaling.
- Dedicated task/execution IAM roles scoped to Bedrock, JWKS and RDS-managed database secret.
- Private ECR, CloudWatch Logs, Secrets Manager, Bedrock Runtime interface endpoints plus S3 gateway endpoint.
- Private PostgreSQL RDS Multi-AZ with encrypted storage, managed master password, retention, deletion protection.
- PostgreSQL-backed API with tenant/domain-scoped evidence, bounded model calls, PostgreSQL advisory-lock quotas and audit records.
- AWS-managed storage and secrets keep credentials out of Terraform variable values.

## Deployment order (separate manual approvals)
1. **Prerequisites:** organization-approved encrypted remote Terraform backend, AWS profile with scoped IaC rights, VPC DNS support, 2 private subnets in **different AZs**, two private route tables, approved endpoint pricing, existing public JWKS secret and allowed Bedrock model.
2. Review `terraform/terraform.tfvars.example`. Never commit real `terraform.tfvars`. Supply actual immutable digest `@sha256:...`; review variable validation and expected monthly costs.
3. Build and scan Docker image using `Dockerfile` from repository root, create ECR repository under approved account, push and **pin digest**. No credentials in the image.
4. `terraform -chdir=deploy/environments/production/terraform init`, `terraform ... fmt -check`, `terraform ... validate`, `terraform ... plan -var-file=terraform.tfvars -out=reviewed.tfplan`. The root needs the data and permission preconditions described above.
5. Before setting `enabled=true` and `approved_release=true`, approve RDS, interface endpoint, ALB and Fargate recurring charges. Terraform will create **billable resources** when enabled.
6. **Database migration:** run `phase28/sql/001_init_postgres.sql` through an approved, private, one-shot migration task/runner *before* allowing the ECS service to serve traffic. Current IaC provisions infrastructure but does **not** automate migrations; without migration, health checks will fail.
7. The ALB now has an internal HTTPS:443 listener with ACM certificate; validate private DNS, certificate hostname and trusted-client network routing; consider private API Gateway/VPC Link and auth at gateway. Do not open external ingress.
8. Run signed OIDC, cross-tenant, RAG, Bedrock, failover, load, recovery, rollback and billing tests. Keep inference disabled until authorized.
9. Production acceptance: `docs/fde/RELEASE_GATES.md` plus external audit/telemetry, JWKS rotation, token/USD budgets, backups/restore drills, traffic encryption and least-privilege DB users.

### Known gaps / operator hold points
- TLS listener + private DNS, database migration automation and non-master DB application user are **required before true production**.
- Static JWKS loaded at task startup; rotate via approved task deployment today.
- Request count quotas are transactional across ECS tasks but **not USD/token budgets**.
- This plan creates endpoints; existing endpoints with same private DNS names must be inventoried to avoid conflicts.
- AWS resource/IAM limits, Bedrock entitlement, endpoint availability and image pull still need real verification.

## Staff engineering commercial workflow increment

The bounded procurement investigation is implemented in `phase28/fde_commercial/`.
An optional separate authenticated MCP service runs on ECS Fargate, routed through
the private HTTPS ALB. The API validates OIDC, uses LangGraph to enforce a fixed
four-node read-only sequence, rechecks tool-result tenant identity, computes PO
variance using Decimal and retrieves scoped policy documents. A verified reviewer
can approve or reject **pending exceptions**. **No ERP change occurs.**

**Safe opt-in:** `enable_commercial_workflow=false` by default. Before enabling,
create a private DNS name matching the ACM certificate, publish approved OIDC
audience tokens accepted by BOTH the API and MCP service, seed synthetic procurement
tables through migrations and verify the authenticated MCP round-trip. The default
RBAC JSON must explicitly grant `procurement` to the proper roles.

**Do not enable for real enterprise customers** until the database master secret is
replaced with scoped application DB credentials, durable audit is enforced,
per-record ACLs are supplied by authoritative systems, and downstream delegation
is reviewed. A delegated audience-bound token exchange should replace forwarding
the original API token across services.
