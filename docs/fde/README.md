# Senior FDE delivery map — LSK AI POC

## Business mandate
Demonstrate how an enterprise commercial-services organization could reduce manual document/status lookup while preventing AI-generated pricing, inventory or transaction changes. Use fictional LSK data; this repository **does not prove an ASR Group production deployment**.

## End-to-end user flow
1. Authorized commercial user submits a question to `POST /v1/business/questions`.
2. FastAPI validates an externally issued OIDC token (issuer/audience/signature).
3. DomainAuthorizer checks user role and requested business domain.
4. SQLite pilot query filters evidence by `tenant_id`, domain and optionally `record_id`. No matching evidence → abstain.
5. If `use_model=false`, API returns authorized source IDs (retrieval-only).
6. If explicitly enabled by both operator flags, API checks local daily model-attempt cap, then invokes approved Bedrock Converse model.
7. Response is parsed, citation-grounded and sanitized-audited. User receives answer or a safe error.

**Real-world boundaries:** Business writes and customer ERP integration are NOT part of this Phase 28 live API. SQLite is not full enterprise vector RAG. Audit and quotas are single-instance controls.

## Delivery ownership
- **Discover:** workshops, business KPI, systems of record, security and acceptance criteria.
- **POC:** prove controlled question → evidence → grounded response and denial behavior.
- **Pilot:** real AWS, IAM/OIDC/Bedrock, synthetic records, operator-visible metrics.
- **Production-style:** ECS managed compute, real connectors with authorization, HA state, SLOs, cost and release governance.
- **Operate:** trace incident to tenant-safe request, contain model errors, rotate credentials, rollback safely.

See `RELEASE_GATES.md` and `../../deploy/environments/README.md`.

## Interview integrity
Say **implemented/tested**, **deployed and verified**, or **proposed** as separate categories. Do not claim measured user adoption, MTTR or production availability without operational evidence.
