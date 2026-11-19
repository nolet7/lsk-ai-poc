# ADR-003 — Bounded LangGraph + authenticated MCP + tenant-scoped evidence

**Decision:** Introduce an explicitly opt-in procurement workflow as a vertical slice,
not an unrestricted generic multi-agent swarm.

## Objective
Help an LSK-style commercial/procurement employee investigate synthetic purchase
order invoice differences and expired supplier certificates. Return verified
numbers, authorized document references, optional Bedrock explanation, and
an optional **pending** exception requiring a different authenticated reviewer.

## Runtime
User -> private HTTPS ALB -> FastAPI JWT (OIDC signature/issuer/audience) ->
DomainAuthorizer(procurement) -> LangGraph (4 deterministic nodes) ->
authenticated MCP read-only service -> tenant-scoped PostgreSQL procurement and
sources -> Decimal price check -> optional Bedrock Converse with guarded citations
-> pending exception proposal -> reviewer-only API (no ERP write).

## Security decisions
- No model-selected tool names; exactly 2 read-only MCP tools, no general SQL.
- MCP verifies the same OIDC JWT itself and derives tenant/roles from verified claims.
- No user-provided tenant/actor/role parameters to tools; result tenant/record
  checked again in graph.
- Only approved synthetic data; data sources are not actual customer ERP/CRM APIs.
- No agent approval tools; separate reviewer role and self-approval prohibition.
- Explicit idempotency key for pending exception; no downstream business mutation.
- Model opt-in remains off by default and consumes the shared per-tenant request quota.
- Avoid placing raw OAuth tokens, questions, document content or prompts in logs.

## Tool and orchestration interfaces
- `phase28/fde_commercial/mcp_server.py`: authenticated MCP resource server.
- `phase28/fde_commercial/mcp_client.py`: one SDK session per API request; sends
  incoming verified token to MCP. **This is a synthetic demonstration**; replace
  with audience-bound on-behalf-of token exchange for real enterprise use.
- `phase28/fde_commercial/graph.py`: fixed four-stage LangGraph. Bounded,
  side-effect free graph, reusable with stub in-process tools for offline tests.
- `phase28/fde_commercial/api.py`: routing, optional model explanation,
  pending proposals and human review.
- `phase28/sql/002_procurement.sql`: synthetic PO/invoice/compliance records
  and idempotent pending exception table.

## Why not autonomous multi-agent execution?
Business totals and approval decisions must be deterministic, traceable and
reproducible. LLMs are used to *explain* authoritative data, never invent
prices, decide identities or authorize transaction mutations.

## Explicit limitations / next release gates
- PostgreSQL records are synthetic; enterprise ERP/CRM/WMS connectors and
  document-level entitlements are not connected.
- Evidence retrieval is tenant+PO SQL, not embedding/hybrid vector RAG.
  Implement S3 ingestion, pgvector search and ACL metadata only after source
  ownership, retention and accuracy evaluation gates.
- MCP shares token audience in this first slice and requires approved private
  DNS/certificate. A separate delegated audience-bound token flow is needed.
- No durable long-running agent checkpoint; each bounded 4-step request is
  retryable but not resumable across process restart.
- Production IaC separates the normal app role from a one-shot master migration task; validate actual RDS grants and credential rotation before external use.
- Quota is request-count only, not true dollar/token cost control.
- Reviewer approval only updates synthetic exception status; never ERP.
- Terraform and CI are static-validated; live MCP+ECS+OIDC tests outstanding.

## Evidence required
Negative 401/403, cross-tenant malformed tool response, nonfinite currency
amounts, idempotency conflict, independent reviewer, agent-step cap, grounded
citations, Bedrock error, MCP timeouts, database restore and load tests.
