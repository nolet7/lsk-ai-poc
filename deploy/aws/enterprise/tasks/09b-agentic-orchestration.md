# TASK 09B — Commercial LangGraph agentic runtime and memory

**Gated after MCP tool contracts and identity controls.** Target specification, not implemented.

## Goal
Unify the four commercial services into a constrained multi-agent runtime. The existing stand-alone report graph is retained as a separate use case, not silently rebranded as the commercial orchestrator.

## Build requirements
1. Create `services/agent-runtime/` with typed LangGraph state: run ID, tenant, verified principal, policy scopes, request intent, allowed tool IDs, evidence/provenance, selected model/prompt version, step/time/token budgets, checkpoint version, reviewer status and audit correlation.
2. Implement supervisor router plus specialist `sales`, `marketing`, `finance`, `document` agents. Plan -> policy -> evidence -> bounded MCP tool selection -> explanation/evaluation -> response/escalation.
3. Integrate the authenticated MCP client; only approved tools visible to each specialist. All downstream tool calls must receive a verified delegated authorization context, not agent-generated credentials.
4. Implement Aurora/PostgreSQL-backed durable checkpoints and idempotency; prove survive pod restart and recover without duplicate commands. Revalidate actor authorization on each resumed run, including after revocation.
5. Bound recursion, steps, wall-clock deadline, per-model token quota, parallel read calls, tool retries and per-tenant cost; deterministic graceful degradation.
6. Business-change intent -> pending proposal -> verified employee review -> separate deterministic workflow/worker; never let the LLM signal approval or directly mutate the ERP.
7. Define proposed API `POST /v1/agents/runs`, `GET /v1/agents/runs/{id}` and event stream only after validating identity and security. Return citations, status, tool provenance, clear model/retrieval-only label, trace id and no secret leakage.
8. Test conversational/multi-turn state isolation, concurrent tasks, prompt injection, malicious MCP output, unauthorized tools, revoked identity, timeout, workflow resume, replay prevention and hallucination refusal.

## Evidence required
- End-to-end Sales, Marketing, Finance and document agent traces with vetted tool calls
- Agent run/checkpoint read after pod kill and restart
- Two users in different tenants cannot access each other's conversations or records
- Step/time/cost limit triggers verified failure/escation without side effects
- Manual reviewer separately authenticates; duplicate proposal remains pending once
- Golden dataset regression evaluation and measured p95 latency

**No claim of production readiness without business and security signoff.**
