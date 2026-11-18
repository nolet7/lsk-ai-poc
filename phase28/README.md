# Phase 28 — Build a live, grounded Bedrock AI assistant (your coding lab)

This branch starts from `feature/aws-enterprise-terraform`. The proven four-service gateway, GitHub packaging, and deployment scripts are preserved. **Nothing in this scaffold is integrated with the running gateway yet.** You write the implementation; a senior engineer will review it.

## CTO mandate
Sales, Marketing, and Finance employees need an assistant that answers questions using their **authorized synthetic business records and policies**, cites evidence, abstains when evidence is insufficient, and NEVER silently changes business transactions. Ship as a measured POC before pilot or production.

## Existing code to reuse (read before you write)
- `integrations/gateway.py`: API key / demo actor identity, FastAPI app, `forward()` to business APIs, hub page
- `integrations/enterprise_api.py`: `POST /v1/platform/ask`, `Ask` request, authorization before retrieval
- `integrations/enterprise_policy.py`: `scope_for()`, `Scope`, fail-closed non-POC policy
- `integrations/acl_retrieval.py`: ACL filtering over `synthetic_knowledge.json`
- `integrations/bedrock_gateway.py`: **existing, working basic Bedrock Converse integration**; enhance rather than replace
- `integrations/agent_tools.py`: existing tool definitions; inspect before adding agent actions
- `compose.business.yml`: gateway + the three pinned private service repositories

## Architecture
```text
Employee (demo browser)
    -> FastAPI gateway identity()
    -> scope_for(actor, domain) [deny before retrieval]
    -> retrieve(question, scope) + optional authorized business insight
    -> grounding guard + budget policy
    -> Bedrock Converse (opt-in, real AWS credentials only)
    -> citation verification + refusal/abstention
    -> audit/metrics (redacted, no raw secrets)
    -> answer with source IDs + actions_taken=[]
```

## Work order (one PR / review checkpoint per task)
- [ ] **P28-01** — Implement `phase28/config.py` safe configuration and ceilings; unit tests
- [ ] **P28-02** — Implement `phase28/grounding.py` evidence extraction, allowed source IDs and citation verification; negative tests
- [ ] **P28-03** — Implement `phase28/budget.py` bounded request token/cost and concurrency policy; tests
- [ ] **P28-04** — Implement `phase28/bedrock_adapter.py`: small testable adapter around existing `integrations.bedrock_gateway`; mock all AWS calls in CI
- [ ] **P28-05** — Implement `phase28/audit.py` privacy-preserving structured audit events
- [ ] **P28-06** — Implement `phase28/service.py` orchestration: authorize -> retrieve -> model -> validate -> return (fail closed)
- [ ] **P28-07** — Add authenticated API integration to `integrations/enterprise_api.py` only after the above pass; keep `use_model=false` behavior and current routes working
- [ ] **P28-08** — Build accessible browser UI in `phase28/ui/` or a gateway-mounted static route, with explicit model-vs-retrieval mode and evidence; no keys in frontend source or URLs
- [ ] **P28-09** — Add comprehensive negative/acceptance tests; attach evidence to your PR
- [ ] **P28-10** — Optional live Bedrock test only after local + CI tests pass and you explicitly approve model cost/permissions (no EC2 required for initial live test)

## Definition of Done
1. `use_model=false` remains deterministic and never invokes AWS.
2. No `BEDROCK_MODEL_ID` => fail closed; no invented answers or fallback pretending to be AI.
3. Source IDs in generated citations are in the **authorized** retrieved evidence set.
4. No tenant crossovers, spoofed new auth paths, or client-chosen AWS model identifiers.
5. No real writes; `actions_taken=[]`; approvals must remain server-side and disabled in this POC.
6. Timeout/throttle/unavailable/malformed-model responses produce safe errors (no stack traces to users).
7. No credentials/PII/unedited raw business evidence in logs.
8. Existing application CI and smoke tests continue to pass.
9. Live call reports model ID, latency, token counts and actual evidence IDs; don't claim production readiness.

## How to work
```bash
git fetch origin
git switch feature/phase28-bedrock-ai-lab
python -m unittest discover -s tests -p 'test_gateway_contract.py' -v
python -m unittest discover -s phase28/tests -p 'test_*.py' -v
```
Phase-28 tests initially contain skipped task reminders. Replace skips with executable positive/negative tests **as you implement each task**. Do not merge incomplete code into the main app.

For review, send the task ID, commit SHA, test commands + outputs, and any tradeoff/ADR decision. I will review correctness, least privilege, tenant boundaries, grounded inference, cost, resilience, tests and code quality.
