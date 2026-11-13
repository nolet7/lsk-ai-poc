# ASR-themed Commercial AI Platform — Release Audit & Gates

**Status: Code improvements committed; no live AWS Bedrock inference, independent security review, business-user pilot or production release has been demonstrated.**

**Scope:** Independent fictional ASR Group-inspired commercial workflows (B2B distributor sales, brand marketing and commercial finance). Not a real ASR Group project and not plant/manufacturing automation.

## Shared architecture
- Gateway with fixed Sales/Marketing/Finance service allow-list; async HTTPX and timeout
- LangGraph agent invokes Bedrock Converse; bounded model-directed tool rounds
- Verified synthetic business facts must appear in the tool trace before a response is presented as grounded analysis
- Read-only tools are always available to a configured model; proposal creation is deliberately gated
- All approval/reviewer endpoints are **untrusted demonstration controls**. Never connect real records or permit general network access.

## POC — functionality and repeatability
Implemented:
- Bedrock and LangGraph code, mocked tool and model tests; fail-closed if model config absent
- Synthetic commercial records, deterministic metrics and human-review simulation
- No-Docker Python launcher, EC2 launch helper, locally scoped ports
- Requests must explicitly opt in to demo proposal creation AND `LSK_STAGE=poc`, `LSK_ENABLE_DEMO_WRITES=true`

Exit gate (NOT YET PASSED):
- Functional test run on a clean local or EC2 instance with valid Bedrock model
- Documented model version, supported tool use, permissions, latency, costs and error behavior
- An adversarial suite including prompt injection, tool misuse and record grounding
- No unintended writes and independently verified service responses

## Pilot — restricted evaluation, not production
Implemented at code level:
- Shared Bedrock/LangGraph code and contract regression tests
- `LSK_STAGE=pilot` and fail-closed demo write/reviewer gate
- Localhost-binding in Compose to avoid exposing demo endpoints to a public network

Required before a real pilot (NOT IMPLEMENTED):
- OIDC/JWT validation with bound user identity and per-record authorization
- User-specific tool permissions, consent and data classification; encrypted managed secrets
- Representative stakeholders, quantitative baseline, evaluation fixtures and manual quality review
- Invocation traces/usage/cost and incident response; rollback and signoff
- Staging deployment in a separate AWS account/environment, isolation and approved egress

## Production — protected baseline only
Implemented at code level:
- Agent code, runtime dependencies, tests, locality on Compose
- `LSK_STAGE=production` blocks the demo's change/review surfaces
- No AWS credentials stored in source

**Release blocker:** This branch is *not deployable as a genuine production business system* without real auth, audited write authorization, secure network ingress, SLOs, operational persistence and approvals. Treat current code as a **release candidate scaffold** for a private synthetic-data demo only.

Required:
1. Verified OIDC + claims authorization propagated to each backend (no X-Actor/X-Role trust)
2. Backend defenses preventing direct calls that bypass the gateway
3. Real business API integration with data-owner approval, idempotency and scoped service identities
4. IaC with private subnets, TLS ingress, managed secrets, VPC endpoints/egress restriction and encrypted durable storage
5. SLI/SLO dashboards (requests, p95, availability, model latency, tool failure, tokens/cost, security events)
6. CI with pinned provenance, SAST/dependency scanning, negative auth tests, model evaluations and signed release promotion
7. Disaster recovery, budget alarms, load testing, rollback drills and operational handover
8. Written security, data governance and business release approval

## Source of truth and promotion
Promote by reviewed change/PR. **Branch names are not deployment environments.** Do not merge POC access controls into a real pilot/production unchanged. Never claim AI is running unless `mode` indicates model execution and Bedrock was invoked successfully.

## How to test current safeguards
```bash
python -m unittest discover -s tests -p test_gateway_contract.py -v
python -m unittest discover -s tests -p test_asr_agent.py -v
python -m unittest discover -s tests -p test_bedrock_ai.py -v
python -m unittest discover -s tests -p test_release_guard.py -v
```
The unit tests use mocks; actual AWS Bedrock inference and real application integration remain separate gated acceptance tests.

References: https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use-client-side.html and https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
