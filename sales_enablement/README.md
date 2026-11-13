# Sales Account Intelligence — Forward Deployed Engineering pilot

A runnable **synthetic-data** internal Sales workflow. It is not a Reddit product, is not connected to Salesforce, and is not production hardened. The original report-demo modules remain unchanged.

## What works

- Seeded SQLite CRM with three fictional accounts, account list and grounded account briefs.
- Optional **real LLM inference** via the OpenAI-compatible chat-completions API; the unconfigured mode is explicitly labeled `deterministic`, not AI.
- Approval-gated account note changes: requester submits, distinct reviewer approves/rejects, then and only then does the application modify the CRM.
- Durable approval records and append-only audit events (application-level, not tamper-proof).
- Read-only MCP tools over local stdio, when optional MCP SDK is installed.
- Unit tests for write gates, rejection, duplicate decisions, and attribution.

## Start on Windows Git Bash or Linux

```bash
python -m pip install -r requirements.txt
export SALES_DEMO_API_KEY="replace-with-a-long-random-local-demo-key"
python -m uvicorn sales_enablement.api:app --reload --port 8010
python -m unittest discover -s tests -v
```

On PowerShell, set `$env:SALES_DEMO_API_KEY="..."` instead of `export`. Never commit a token.

## End-to-end exercise

```bash
curl -H 'X-API-Key: replace-with-a-long-random-local-demo-key' -H 'X-Actor: sales.user' http://127.0.0.1:8010/accounts
curl -H 'X-API-Key: replace-with-a-long-random-local-demo-key' -H 'X-Actor: sales.user' http://127.0.0.1:8010/accounts/acme/brief
curl -X POST http://127.0.0.1:8010/change-requests -H 'Content-Type: application/json' -H 'X-API-Key: replace-with-a-long-random-local-demo-key' -H 'X-Actor: sales.user' -d '{"account_id":"acme","proposed_note":"Customer approved the next technical review.","reason":"Confirmed during call"}'
```

Copy the returned `id`, then approve **with a different actor**:

```bash
curl -X POST http://127.0.0.1:8010/change-requests/REPLACE_ID/decision -H 'Content-Type: application/json' -H 'X-API-Key: replace-with-a-long-random-local-demo-key' -H 'X-Actor: team.lead' -H 'X-Role: reviewer' -d '{"approve":true}'
```

Read the account again to verify the note changed; see `/audit-events` with reviewer headers.

## Real model mode

Set `OPENAI_API_KEY` and optionally `SALES_LLM_MODEL` before starting the app. The service sends only **synthetic** account records to the configured HTTPS chat-completions endpoint. LLM failures return an error rather than pretending a deterministic response is model-generated. In this pilot, model inference creates a brief; it **never** directly updates CRM records.

## Optional MCP

```bash
python -m pip install mcp
python -m sales_enablement.mcp_server
```

MCP tool transport is local stdio and relies on the trusted local process boundary. Do not expose this demo MCP server remotely without adding real authentication, authorization, and transport protections.

## Definition of done / remaining work

This pilot is a narrow working vertical slice, not a complete Reddit-ready enterprise service. Still required: SSO and verified RBAC (headers are spoofable), tenant-aware data access, CRM OAuth integration, prompt injection tests, role-aware retrieval, managed secrets, cross-process locking, distributed durability, background jobs, UI, meaningful task evals, performance and cost dashboards, CI/CD, deployment environments, baseline/user studies, pilot adoption evidence and operational handover. The generic `agents/graph.py` report workflow is intentionally still legacy and still needs bounded retries. **Do not call this production deployed.**
