# Production release gate and operating runbook — NOT APPROVED

This branch is a **production-stage scaffold**, not an operationally approved LSK system.
All data must remain synthetic. No actual LSK sponsorship or deployment is asserted.

## Mandatory predeployment controls
- OIDC/JWT-signed user and service identity; authorize domain and each record at every backend. Remove trust in X-Actor/X-Role.
- Block direct business-API access from clients. TLS ingress, network isolation, secrets management, encryption at rest and transit.
- Approved Bedrock model or inference profile and scoped `bedrock:InvokeModel` IAM role on compute, with no static access keys.
- Model, prompt, API schema and app versions pinned and signed. Build provenance and vulnerability scan.
- Tested human approval workflow and immutable audit destination for consequential actions; no model direct writes.
- Real-data classification and retention policy, DLP, redaction and prompt-injection testing.
- Staging load tests, failure injection, rollback and recovery exercises; published ownership and escalation rota.

## Observability baseline
- `GET /health`: process liveness only
- Authenticated `GET /ready`: upstream synthetic service reachability and configured model identifier, **not proof that Bedrock access works**
- `GET /internal/metrics` on loopback: request volume/status and route-template latency (no prompt/customer labels)
- Add Bedrock token counts, actual per-request costs, model/tool tracing and SLO alerts before release
- Proposed SLOs for stakeholder review: 99.9% API availability; response latency/error budgets by task complexity; no unauthorized writes. **No target is achieved until measured.**

## Safe degradation
Bedrock invocation fails: no fake AI answer, return an error. Missing verified source: fail closed with an ungrounded-response warning. Upstream service unavailable: return a dependency/agent error. All demo writes are blocked at this stage.

## Rollback procedure
1. Stop deployment and disable the agent API route at ingress; preserve read-only access where approved.
2. Roll back to last signed image, configuration and pinned app contracts after operator approval.
3. Confirm identity/authorization, dependency readiness and customer-impact checks.
4. Validate DB schema rollback and restore from tested backup if migration changes require it.
5. Review incident evidence, model/tool logs with privacy controls, and issue release signoff.

## Required approval
Security lead, platform owner, commercial business owner, data governance and on-call operations lead must approve a release with dated evidence. **This approval has not occurred.**
