# FDE delivery brief — Sales Account Intelligence pilot

## Business problem (hypothesis, not stakeholder-validated)
Sales teams spend time consolidating account context before calls, and hand-written CRM updates can be inconsistent. Build an internal account brief with cited CRM fields; allow note updates only after independent human approval. All current accounts are fictional.

## Discovery guide (interview actual users before claiming adoption)
1. Sales representative: Which account research tasks are repetitive? How long does each one take? Which information is authorized?
2. Sales manager: What account updates require approval? Who is accountable for accuracy?
3. Security and IT: Which CRM fields can be indexed and shared? What identities and audit retention rules apply?
4. AI Platform Hub: What connector, model, evaluation, telemetry, and identity services should be reused?

## Jobs to be done
- Before a customer call, compile a concise account brief using approved CRM facts.
- After a call, request a CRM note with clear provenance and business justification.
- As a team lead, approve or reject changes and preserve an audit trail.
- As a platform owner, identify exceptions and reuse safe tool patterns.

## Baseline and pilot measures
Collect observations, not fabricated impact claims. Store participant IDs pseudonymously and obtain approval before collecting usage analytics.

| Measure | Baseline collection | Pilot collection | Proposed target |
|---|---|---|---|
| Research time | Timed manual account brief on 20 fictional accounts | Timed app workflow with same account set | 50% lower median |
| Grounding accuracy | Two reviewers grade facts against source records | Same rubric after model changes | >= 95% verified statements |
| Unauthorized CRM writes | Attempt unapproved and self-approved writes | Repeat using API and UI tests | 0 successful |
| Manual effort | Number of user steps per completed task | Same metric through portal | Reduction without error increase |
| Adoption | Eligible cohort size and weekly workflow volume | Weekly opted-in active users | >= 70% of pilot cohort |
| Cost | Employee time per completed brief | Human time plus LLM/API costs | Lower total cost per acceptable brief |

Measure latency p50/p95, model spend, error rate, and rejected output rate independently. Do not equate task success with passing formatting checks. Record model, prompt version, source snapshot, evaluator version, and approval outcome.

## Acceptance criteria
- User can select a fictional account and receive a brief with source fields.
- Output clearly identifies whether a model or deterministic logic generated it.
- Any write first creates a pending request; no CRM mutation occurs before a distinct reviewer approves.
- Rejecting a request preserves existing account data.
- Duplicate approvals fail and decisions are auditable.
- Reviewer access is cryptographically verified before any real deployment; current header-based demo is not sufficient.
- Tests run on pull requests and documentation includes setup, incident procedures, and limitations.

## Ownership and handover
- Business owner: assign a Sales operations lead during discovery.
- Technical owner: assign application maintainer and on-call team before pilot.
- Risk owner: security reviewer signs off before access to real customer information.
- AI Platform owner: maintain shared tool contract, eval dataset and deployment pattern.

## Rollout gates
POC: local synthetic data, deterministic and optional LLM modes, read-only MCP.
Pilot: business UI, signed identity, allowed CRM scopes, realistic test fixtures, trace/metric instrumentation and user feedback.
Production: reviewed OAuth connector, tenant ACLs, database migrations, immutable audit storage, operational runbooks, CI/CD and reliable rollback. Require stakeholder signoff and measured benefit.
