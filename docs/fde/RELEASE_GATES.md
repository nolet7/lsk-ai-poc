# Release evidence and go/no-go gates

Mark a gate PASS only after attaching evidence. Empty cells indicate unverified, not failure.

| Gate | POC | Pilot | Production-style | Evidence |
|---|---|---|---|---|
| Source commit and signed/reviewed release | Required | Required | Required | full SHA, artifact digest |
| Offline unit/security regression | Required | Required | Required | CI URL/test output |
| AuthN, AuthZ, tenant-isolation negative tests | Required | Required | Required | sanitized test logs |
| Grounding/no-evidence abstention | Required | Required | Required | response/citation sample |
| Live provider invocation in target account | Optional | Required | Required | model/region, safe request ID |
| Cloud IAM, private networking, no secrets in source | N/A | Required | Required | plan/role/endpoint review |
| SLOs, cost caps, request budgets and alarm drills | Document | Measure | Enforce and test | dashboards/alerts |
| Immutable rollout, rollback and restore | Document | Exercise | Enforce and rehearse | runbooks/drill |
| Managed durable multi-AZ storage and DR | N/A | Gap documented | Required | restore/chaos evidence |
| Scoped ERP/CRM integrations | Synthetic | Synthetic or approved read-only | Required if in scope | API contracts/access review |
| Security and business approval | Local owner | Pilot owner | Security/IT/product sign-off | approval record |

## Known evidence today
- Local `phase28` test report: 174 passed, 10 skipped (user-provided run).
- GitHub Actions Linux test run: https://github.com/nolet7/lsk-ai-poc/actions/runs/44438059681 (success).
- IAM provisioning: request submitted; final result not yet evidenced.
- Cloud EC2 installation and live Bedrock inference: not yet evidenced.

Before interviewing, attach real logs, timestamps, test reports and architecture decisions. Synthetic lab data is not customer production data.
