# Stage promotion requirements and operational readiness

The source architecture review sets the following strategy. **These are targets and gates, not achieved production metrics.**

| Layer | POC | Pilot | Production |
|---|---|---|---|
| Data | Synthetic | Sanitized/approved sample | Authorized tenant data only |
| Model | Enabled Bedrock test model, explicit read-only mode | Version-pinned approved candidate | Validated, monitored and rollback-capable |
| Identity | POC key with localhost isolation | Real signed OIDC, workload identity | Tenant/record ABAC, TLS, service-level authorization |
| Commands | Pending synthetic proposals only | Reviewed durable workflow and idempotency | Approved audited business command service |
| Infrastructure | Local/isolated low-cost | Production-like isolated environment | Multi-AZ private cluster, managed state, verified DR |
| Delivery | Unit/integration tests | Security/quality evaluation and rollback drill | Signed builds, gated progressive rollout |
| Monitoring | HTTP/model errors in CI | Trace and service metrics + baseline | SLO dashboards, paging independent of AI |
| Governance | Architecture decisions | Privacy/security review and UAT | Signed business/security/platform acceptance |

## Suggested service objectives (must be approved and measured)
- AI gateway monthly availability: **99.9% proposed**, not achieved.
- Customer transaction data: **5–15 minute RPO; 1 hour RTO**, proposed.
- Stateless AI inference: **30 minute RTO**, proposed.
- RAG index: rebuildable from controlled, versioned source, **4 hour RTO**, proposed.
- Model registry metadata: **1 hour RPO / 4 hour RTO**, proposed.
- Experimental training: **24 hour RPO/RTO**, proposed.
- Demand-based model timeout; measurable p95 latency, failure budgets and maximum cost per task must be accepted before production.

## 8 production gates
- [ ] Threat model, network zones, OIDC/workload identity, tenant/record authorization, secrets and TLS reviewed
- [ ] Data ownership, classification, lineage, retention and verifiable deletion
- [ ] Evaluated prompt/model versions, injection tests, tool-safety and retrieval-authorization red team checks
- [ ] Multi-AZ, load tests, failure drills and restored backups that meet approved RPO/RTO
- [ ] On-call ownership, observability, independent paging, runbooks and rollback
- [ ] Reproducible Terraform/Helm/Argo CD delivery, signed images and supply-chain scanning
- [ ] Token cost/FinOps attribution, quotas, model inference sizing and approved budget limits
- [ ] Product owner UAT, impact baseline and security/data governance signoff

## Current truth
The `main` branch implements the LSK commercial synthetic POC. It has no approved real tenant identity, no ERP write integration, no HA state service, and no independent production security review. The named six reference architectures are not all deployed. An example Kubernetes workload is included for design review; it must **not** be promoted as a real production environment without the gates above.

### Operator checks
```bash
python -m unittest discover -s tests -p test_gateway_contract.py -v
python -m unittest discover -s tests -p test_enterprise_architecture.py -v
docker compose --env-file .env.business -f compose.business.yml config
```

Real Bedrock acceptance separately requires approved model access, a scoped EC2/EKS workload role, verified latency and token cost. AWS credits do not imply access or free inference.


## Cross-repository integration CI authentication

The Sales, Marketing, and Finance applications are separate GitHub repositories, which may be private. The default `GITHUB_TOKEN` for `lsk-ai-poc` does not automatically grant access to them. The `four-service-smoke` workflow is **skipped until authorized**, not counted as evidence of a passing integration test.

Configure an authorized GitHub App with read-only Contents access to the three business repositories; store its App ID and private key in this repository's GitHub Actions secrets:

- `LSK_INTEGRATION_APP_ID`
- `LSK_INTEGRATION_APP_PRIVATE_KEY`

Then create the repository variable `LSK_INTEGRATION_ENABLED=true`. The job uses a short-lived GitHub App token, checks out pinned SHAs from `integrations/app-versions.env`, verifies them, and runs `scripts/smoke_business.py` against four actual FastAPI processes with temporary synthetic databases. No Bedrock costs are incurred.

A green run with the smoke job **skipped** is only unit/API contract validation. A completed smoke job is needed for the integration acceptance gate. Do not grant private keys or broader repository permissions merely to make a test green.
