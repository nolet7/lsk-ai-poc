# LSK AWS Enterprise Platform — Terraform hands-on learning track

**Branch:** `feature/aws-enterprise-terraform` (the enterprise Terraform branch; the earlier EC2 Compose lab is retained for comparison). Existing `deploy/aws/ec2/` remains an isolated reference lab, **not the enterprise deployment**.

## How the exercise works
Do **exactly one task at a time**. Complete the task, paste the evidence requested (redact AWS account IDs, resource ARNs, tokens, public IPs and secrets), then request an acceptance review. The next task remains gated until the previous one passes. The assistant cannot directly observe your personal AWS account unless you provide non-sensitive command output or connect an authorized tool. Do not paste credentials, Terraform state, or `.tfvars` containing secrets.

## AI platform design (review update)

**Full runtime:** [AGENTIC_AI_ARCHITECTURE.md](AGENTIC_AI_ARCHITECTURE.md) describes the MCP tool services, AgentCore Gateway vs private MCP decision, LangGraph supervisor and specialist agents, Aurora checkpoints, ACL-first RAG, S3 ingestion, embeddings and hybrid retrieval, Bedrock model router, prompt registry, Bedrock Guardrails, AI evaluations and telemetry. These are **design targets**, not completed deployments.

**Task 09 is split into four separate gated labs** so model access does not obscure authorization and tool-execution safety:
- [09A MCP and delegated identity](tasks/09a-mcp-platform.md)
- [09B agentic LangGraph and memory](tasks/09b-agentic-orchestration.md)
- [09C RAG and document intelligence](tasks/09c-rag-document-intelligence.md)
- [09D LLM gateway, prompts and evaluation](tasks/09d-llm-model-governance.md)

These subtracks have dependencies rather than a strict mandatory execution order: MCP and RAG contracts should be validated before the commercial agent graph; the model gateway can be implemented with stub inputs independently. Do not connect them to actual users until OIDC authorization tests pass. **Task 01 remains first and unchanged.**

## Dedicated Kubernetes operations folder

[**Kubernetes operations implementation track**](kubernetes/README.md) defines the EKS platform, AWS Load Balancer Controller, managed node groups / conditional Karpenter, Helm application starter chart, Argo CD manual-sync starter, day-2 operations, security boundaries and acceptance tests.

- [Task 04A — EKS operations and autoscaling](tasks/04a-kubernetes-operations.md)
- [Task 06A — Helm, Argo CD and GitOps](tasks/06a-helm-argocd.md)

**Design status:** The chart and Argo Application are templates, not executed releases. Cluster Terraform modules, per-service production charts and Karpenter installation are task deliverables, not yet implemented. **Task 01 remains the first step.**

## Architecture decisions
- **Target:** Separate nonproduction and production AWS accounts, three AZs, private EKS nodes and service pods, dedicated IAM roles with EKS Pod Identity, private Aurora PostgreSQL with encrypted storage, S3 documents, Bedrock read-only inference, queue-backed approved proposals, OIDC workforce identity, ALB/WAF/TLS, CloudWatch + OTel + Prometheus/Grafana, GitHub Actions build and Argo CD GitOps deploy.
- **IaC:** Terraform modules for network, cluster, identities, secrets, data and observability; one state per account/environment/component. Terraform resources and Kubernetes/Helm workloads have explicit ownership boundaries. Avoid a single enormous root state.
- **Terraform backend:** S3 versioned bucket, encryption, public-access block, TLS enforced, **S3-native lock files** `use_lockfile = true`, not new DynamoDB locking. Lock and state permissions must be least-privilege.
- **Deployability:** The current commercial gateway uses shared POC API keys, server-set synthetic tenant and SQLite. It deliberately fails closed in pilot/production. Infrastructure can be provisioned safely ahead of application migration, but **production traffic stays blocked** until OIDC/tenant claims, managed state, ACL, key rotation, approval service, and security review pass.
- **Data:** Sales, Marketing and Finance are independent apps: do not treat them as one shared transaction-writing database. Each owns its schema, credentials and API contract. Aurora PostgreSQL can initially host **separate isolated databases/users**; a shared cluster is an explicit failure-domain tradeoff.
- **Ingress:** EKS AWS Load Balancer Controller -> ALB with ACM TLS + WAF, private Kubernetes services, identity validation in apps/auth boundary; never trust client-supplied X-Actor for production.
- **Cost:** Multi-AZ NAT, EKS control plane, Aurora, ALB, managed observability and Bedrock are billable. `terraform plan` does not provision paid infrastructure. Get cost approval before applies, keep budget alarms; budgets are notification tools, not spending hard caps.
- **Target SLOs:** 99.9% gateway monthly (proposed), set baseline latency/error/Bedrock-cost goals, prove with instrumentation and synthetic probes rather than claiming achieved results.
- **Safe integration:** No real ERP/payment writes or real data until business acceptance; inference and retrieval must remain scoped to verified actors/tenants.

## Planned repository tree
```text
deploy/aws/enterprise/
  README.md
  ARCHITECTURE.md
  tasks/
    01-prerequisites.md                <-- START HERE
    02-terraform-remote-state.md
    03-network-foundation.md           (implementation gated)
    04-eks-platform.md                 (implementation gated)
    04a-kubernetes-operations.md       (implementation gated)
    05-identity-and-secrets.md         (implementation gated)
    06-build-ecr-ci.md                 (implementation gated)
    06a-helm-argocd.md                 (implementation gated)
    07-business-services.md            (implementation gated)
    08-data-and-messaging.md           (implementation gated)
    09-ai-rag-bedrock.md               (parent integration gate)
    09a-mcp-platform.md                (implementation gated)
    09b-agentic-orchestration.md        (implementation gated)
    09c-rag-document-intelligence.md    (implementation gated)
    09d-llm-model-governance.md         (implementation gated)
    10-edge-identity.md                (implementation gated)
    11-observability-reliability.md    (implementation gated)
    12-security-dr-and-promotion.md    (implementation gated)
  terraform/
    bootstrap/        <-- one-time protected state S3 bucket (task 02)
    environments/     <-- created and reviewed in task 03+
    modules/          <-- created and reviewed in task 03+
  kubernetes/         <-- EKS ops specs + Helm chart + GitOps starter, task 04+
  gitops/             <-- task 06+
```

## Gate definitions
| Task | Objective | Evidence to submit |
|---|---|---|
| 01 | AWS CLI, Terraform, identity, region, least-privilege authorization, budget | Redacted versions, identity summary, budget screenshot/details, `terraform fmt -check` |
| 02 | Bootstrap state bucket and S3 native locking setup | Redacted `plan`, `apply`, S3 versioning/block/public encryption verification |
| 03 | Terraform VPC, 3 AZ, routes, isolated public/private/data subnets, endpoints | Plan review, subnet/routes, `terraform output`, no direct inbound to workloads |
| 04 | Private EKS nodes, cluster add-ons, autoscaling and RBAC | cluster health, node readiness, non-admin kubectl, upgrade plan |
| 05 | EKS Pod Identity roles, Secrets Manager, KMS, trust and permission tests | positive + negative role isolation tests |
| 06 | ECR, CI pinned builds, scan/sign/push and Argo CD promotion | immutable digest, CI logs, GitOps sync/rollback evidence |
| 07 | Gateway + three apps as independently deployed services | service endpoints, health probes, four-service smoke, no public app ports |
| 08 | Aurora, per-app schemas/users, SQS/DLQ, migrations and backups | tests showing durability, idempotency, DB isolation and restore |
| 09A | MCP tool servers, gateway, delegated identity | scoped discovery, denied cross-tenant calls and audit trace |
| 09B | Commercial LangGraph agents and checkpoints | runs survive restart, tool constraints and approvals |
| 09C | RAG pipeline, ACL-aware vector search, ingestion | index provenance, citations, tenant/revoke/delete tests |
| 09D | LLM model routing, prompts, guardrails, evaluations | model quality gates, cost/latency, fail closed |
| 09 | Integrate all four AI components | end-to-end authenticated agent task and adversarial evaluation |
| 10 | Authenticated public entry (or private workforce access), TLS/WAF, OIDC | denied unauthenticated access, verified claims and record-level auth |
| 11 | SLOs, traces, alerts, scaling, chaos/failure drills | dashboards, alert fire, rollback and load results |
| 12 | threat model, supply chain, DR, UAT, production approval | signed gate checklist and rollback/restore results |

## Promotion rules
POC uses only synthetic records and no externally exposed shared-key APIs. Pilot requires real OIDC and approved sample data; production requires the full eight gates in `docs/RELEASE_GATES.md`. All Terraform applies require plan review and human approval. Do not use `-auto-approve` in this track. Never `terraform destroy` shared backend resources.

## Official learning references
- [Terraform S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3)
- [AWS EKS best practices](https://docs.aws.amazon.com/eks/latest/best-practices/introduction.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [AWS Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
