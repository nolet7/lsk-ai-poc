# Senior architecture review — Kubernetes operations corrective actions

**Review scope:** `feature/aws-enterprise-terraform`, gateway chart and infrastructure plan. **Current status: POC templates only, no AWS resources applied.** 

## Critical gaps found and disposition

| Severity | Finding | Resolution in branch | Further required |
|---|---|---|---|
| HIGH | Deployment references a non-existent ServiceAccount | ServiceAccount template added | EKS Pod Identity associations and RBAC validation in Task 05 |
| HIGH | Prior chart allowed arbitrary replica counts despite local SQLite state | Chart enforces one replica, demo writes disabled | Migrate durable commands/checkpoints to Aurora before HPA/multi-replica |
| HIGH | Missing explicit private network control | ClusterIP retained; ingress NetworkPolicy added | Validate VPC CNI network policy mode, policies and actual deny test |
| HIGH | Invalid stages might render via Helm values | Validations and JSON schema fail closed on non-POC, public service, missing secret/digest | OIDC replacement and production chart acceptance |
| MEDIUM | Incomplete baseline pod controls | Non-root UID, RuntimeDefault seccomp, no privilege escalation, all capabilities dropped | Confirm runtime filesystem/pod security in actual EKS |
| MEDIUM | No startup probe / graceful termination | Startup probe and 30s termination grace added | Load test shutdown, DB connection handling and actual app readiness |
| HIGH | GitOps example uses Argo CD default AppProject | Example remains intentionally unusable without reviewed revision and overrides | Implement AppProject repository/destination RBAC, SSO, signatures and policy in Task 06A |
| HIGH | No Terraform EKS resources implemented | Tasks and ownership boundaries documented | Implement separate network, EKS, IAM and data modules during Tasks 03–05 |
| HIGH | No Karpenter implementation/capacity tests | Managed-node-first decision recorded | Build NodePool/EC2NodeClass only after measuring scheduling needs and interruption tolerance |
| HIGH | No dependency protection / app environment identity | No public Ingress and non-POC chart blocked | Enterprise OIDC/record policy, secrets rotation, approvals and audit evidence |
| MEDIUM | Hub links point to localhost | Kept POC-only | Make URLs configurable / route via authenticated BFF in Task 07 |
| MEDIUM | Chart health returns process liveness, not dependencies | Explicit readiness caveat | Add /ready dependency checks and SLO instrumentation for enterprise runtime |

## Operational ADRs

### ADR-015 — Separate Terraform infrastructure from Argo CD application ownership
Terraform provisions AWS network, EKS, IAM, ECR, DNS foundation and managed state. The GitOps controller owns application deployments, services, configuration, pod policies and app charts. Argo bootstrap ownership must be documented to avoid Terraform/Argo reconciliation fights. `ApplicationSet` later only with reviewed project policies.

### ADR-016 — Managed node groups before Karpenter
Use private managed nodes for predictable lab capacity and stable system add-ons. Test HPA for stateless pods only when database state is externalized. Introduce Karpenter separately for heterogeneous/on-demand/spot capacity with interruption handling, tagged discovery, NodePool limits and disruption budgets. HPA scales pods; Karpenter or another node autoscaling mechanism adds EC2 nodes. Never assume managed node groups **automatically** scale on unschedulable pods without configured node autoscaling.

### ADR-017 — POC isolation is deliberate
No internet exposure. Pilot/production manifests must be *new application revisions* with real identity, managed durable storage and business authorization. The sample chart has `LSK_STAGE=poc`, one replica and a pre-existing secret required. Do not label the cluster production-ready just because it is multi-AZ.

### ADR-018 — Secrets/config and rollout
Secret rotation alone does not necessarily reload process environment variables. Use reviewed rollout/restart orchestration and test credential refresh. Do not put secret literals or sensitive `helm --set` values in Git, Terraform state or CI logs. Pin ECR immutable image digest; AppProject allowlists, branch protection, approval gates, admission policy and image signing required before promotion.

## Verification to perform
1. Install compatible Helm v3; run `bash deploy/aws/enterprise/kubernetes/tests/check-gateway-chart.sh` for render and negative controls.
2. In nonprod EKS, verify private nodes, CNI policy enforcement, Pod Identity and denied AWS access, network-denied ingress, app health, and absence of public LoadBalancer/Ingress.
3. Test startup and rolling restart, missing/updating Secret, malicious image injection, pod killed during tool call, and deterministic fallback without model.
4. Only after Aurora migration, test replicas >=2, PDB, HPA, AZ rescheduling and node provisioner behavior.
5. Capture actual cost and infrastructure acceptance; do not infer Terraform code exists merely from this design.

## Open risks before enterprise pilot
OIDC/tenant ACL, Aurora schema migration, MCP user delegation, RAG ACL storage, durable agent checkpoints, audit-grade approvals, CI supply-chain gates, multi-AZ restores, and independent SRE paging are not delivered by this chart.
