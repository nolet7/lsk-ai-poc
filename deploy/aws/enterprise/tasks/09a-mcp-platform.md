# TASK 09A — Enterprise MCP platform, tool registry and delegated identity

**Gated after Tasks 01–08, before production authorization/inference.** Target specification, not implemented.

## Business requirement
Provide approved agent tools for Sales, Marketing, Finance and supplier/contract documents, with centrally controlled discovery and strictly enforced business-record permissions. MCP is a tool interaction protocol, **not** a replacement for identity, business APIs or policies.

## Architecture and implementation
1. Create `services/mcp/{sales,marketing,finance,documents}/` with official MCP Python SDK and Pydantic-validated schemas. Implement private authenticated HTTP transport appropriate for the selected SDK version; do not expose localhost-only development transport publicly.
2. Implement read-only tools: `sales.list_accounts`, `sales.account_insight`, `marketing.campaign_performance`, `finance.invoice_variance`, `documents.search_authorized`. Call the existing authoritative application APIs; prohibit database bypass and make tools deterministic.
3. Build `services/mcp-gateway/` with static allowlist, tool version registry, policy decision call, timeout, quota, circuit breaker, audit emitter. Compare to **Amazon Bedrock AgentCore Gateway** in an ADR including managed service pricing, OAuth inbound, outbound on-behalf-of, VPC reachability, supported MCP transports and isolation.
4. Bind verified user/tenant/entitlement context to downstream requests with short-lived, audience-bound delegated credentials and service-to-service authorization. Do not just forward client `X-Actor`, `X-Role` or agent-chosen tenant strings. Require authorization again in each business API.
5. Define per-tool scopes and per-actor/per-tenant/per-record entitlements. Disallow non-approved tools and cross-tenant target ids; record tool_id, decision_id, trace_id, status and cost, but no secrets/PII.
6. Do not expose approval execution, payment posting or ERP writes as model-callable tools. Model may create **pending** proposal only through scoped, idempotent command boundary.
7. Deploy MCP services as private EKS Kubernetes Deployments with separate Pod Identity roles, service accounts, probes, network policies, HPA if measured, resource quotas and ECR digests. Add GitHub Actions and Argo CD change promotion.
8. Implement unit, integration, contract and adversarial tests including malformed JSON, forged tenant, forged actor, tool-injection response, expired token, unauthorized tool, timeout/retry, and duplicate writes.

## Evidence required
- MCP SDK/client live discovery of tools with schemas and version
- Allowed Sales read and denied cross-tenant Finance record via same gateway
- Revocation/expiry and user-delegation test through MCP server AND business API
- Agent cannot discover or execute forbidden write tools
- Four-service integration remains functional when MCP or Bedrock fails
- Latency and call failure traces, IAM/network negative tests, resource plan, cost breakdown

**Stop for review; do not promote without validated identity delegation.**
