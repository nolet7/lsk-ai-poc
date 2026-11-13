# Cross-repository Enterprise AI Enablement Integration

## CTO mandate and scope
Connect independently deployable Sales, Marketing and Finance applications to one AI Enablement gateway. Standardize discovery, grounded business insights, and human-approved change requests. Use deterministic automation for arithmetic and policy decisions; use optional LLM inference for explanatory summaries. The portfolio uses exclusively fictional data.

Applications:
- [Sales Account Intelligence](https://github.com/nolet7/lsk-sales-account) — account briefs, opportunities, approval-gated notes
- [Marketing Intelligence](https://github.com/nolet7/lsk-marketing) — CTR, conversion rate, cost per conversion, optimization proposals
- [Finance Invoice Review](https://github.com/nolet7/lsk-finance) — three-way match and exception handling without payment execution

## Architecture
```text
Employee -> AI Enablement Gateway (:8090)
                   | async HTTPX; fixed service allow-list
       +-----------+------------+
       |           |            |
   Sales :8101  Marketing :8102 Finance :8103
       |           |            |
     SQLite      SQLite       SQLite   (isolated synthetic data)
       |           |            |
   Insight + independent human approval + audit log
```

The existing LangGraph report workflow in this repository is separate; the gateway demonstrates HTTP integration between independently deployed business systems and is not yet wired into the LangGraph graph as agent tools.

## Launch all four services using Docker Desktop

Requires Docker with Compose, Git, and a shell (Git Bash on Windows works).

```bash
git clone https://github.com/nolet7/lsk-ai-poc.git
cd lsk-ai-poc
bash scripts/clone_business_apps.sh
cp .env.business.example .env.business
# Edit .env.business and set long random GATEWAY_API_KEY and DEMO_API_KEY values.
docker compose --env-file .env.business -f compose.business.yml up --build
```

If already inside the central repository, do not clone it again; run commands from its root. Docker builds local clones in `external/`, which are intentionally not committed.

Open the hub at http://localhost:8090, or individual employee portals:
- http://localhost:8101/portal
- http://localhost:8102/portal
- http://localhost:8103/portal

API docs: http://localhost:8090/docs

## Common versioned API
- `GET /health` (public liveness only)
- `GET /v1/apps` (concurrent service discovery, reports unavailable services)
- `GET /v1/apps/{sales|marketing|finance}/records`
- `GET /v1/apps/{domain}/records/{record_id}/insight`
- `GET /v1/apps/{domain}/proposals`
- `POST /v1/apps/{domain}/proposals` with `{"record_id":"...","text":"...","reason":"..."}`
- `POST /v1/apps/{domain}/proposals/{id}/decision` with `{"approve":true}`
- `GET /v1/apps/{domain}/audit`

Gateway headers: `X-API-Key: <GATEWAY_API_KEY>` and `X-Actor: demo.employee`. An independent reviewer submits `X-Role: reviewer` (simulated, **not verified identity**). The gateway injects the separate service key upstream.

```bash
curl http://localhost:8090/health
curl -H "X-API-Key: YOUR_GATEWAY_KEY" -H "X-Actor: employee.one" http://localhost:8090/v1/apps
curl -H "X-API-Key: YOUR_GATEWAY_KEY" -H "X-Actor: employee.one" http://localhost:8090/v1/apps/marketing/records
```

## Acceptance demonstration
1. Discover all three services from the gateway.
2. Generate Sales account research with explicit `mode` and source evidence.
3. Check Marketing metrics against an independent calculator.
4. Identify Finance invoice/PO/receipt mismatch using deterministic arithmetic.
5. Submit a proposal; verify records are unchanged before approval.
6. Deny self-approval; approve using a distinct reviewer; inspect audit history.
7. Stop one service; verify gateway discovery reports it as unavailable rather than hiding failure.

## Security and release restrictions
The demonstration uses shared secrets and **spoofable caller/reviewer headers**, local SQLite and HTTP within Docker networking. This is NOT production authentication, tenancy, governance, or a secure deployment. No real personal, customer, finance or payment information. The Finance application only annotates and marks synthetic exceptions; it never pays, adjusts a ledger, or triggers funds transfer.

Before any genuine pilot: OIDC/JWT-signed identity and RBAC, scoped service credentials, TLS, managed secrets, tenant authorization, signed audit evidence, SLOs, proper async DB/pools, bounded retries, real workflow/eval datasets, SIEM/telemetry, business-owner approval and rollback testing. Do not present proposed success targets as achieved.
