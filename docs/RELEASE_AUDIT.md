# Three-stage release engineering audit — ASR-inspired commercial AI

**Classification:** Independent fictional enterprise portfolio project. Not sponsored,
endorsed or deployed by ASR Group. All customer, marketing and finance records
are synthetic. No manufacturing equipment or plant maintenance workflows.

## Shared implemented foundation
- Real AWS Bedrock Converse integration (only when model/IAM access is configured)
  with a bounded LangGraph agent and selected read-only business tools.
- Separate Sales, Marketing and Finance APIs; deterministic calculations and
  approval-pending proposal workflow only for an explicitly opted-in isolated POC.
- AI cannot approve a proposal, alter a financial ledger or execute payment.
  Proposals require a verified prior read of the *same record*.
- Gateway and business services independently check signed OIDC bearer JWT
  issuer, audience, expiry, RS256 signature and domain claims for pilot/production.
  Demo API keys alone cannot authenticate a user in these stages.
- Pin SHA revisions of each standalone business repository; scripts synchronize
  only clean checkouts with explicit confirmation.
- Four-service no-Docker launcher, SSH-only EC2/systemd deployment files,
  CloudFormation EC2 instance profile with scoped Bedrock invocation resource ARNs.
- Request count/status/latency and Bedrock model result Prometheus metrics;
  staging metrics require dedicated scrape secret.
- Negative security tests, signed-token crypto tests, mocked agent tests,
  deterministic evaluation tests and a four-process HTTP smoke suite.
- A live-model read-only evaluation harness producing JSON evidence per task.

## POC — feature complete for synthetic lab execution, live acceptance pending
**Implemented:** synthetic workflows, opt-in model, LangGraph tool use, gateway,
isolated demo approvals, CI unit/smoke checks, local and EC2 launch procedures.
**Access:** POC gateway uses a demo key. Backend write operations require BOTH
`LSK_STAGE=poc` and `LSK_ENABLE_DEMO_WRITES=true`; disabled by default.
**Unverified:** actual AWS Bedrock invocation, model choice/usage charges,
live latency, real FDE task score, AWS VM provisioned and running.
**Promotion requires:** clean CI, successful live Bedrock scenario, grounded
record citations, negative prompt-injection tests, budget and performance report.

## Pilot — code-ready for synthetic evaluation, organizational onboarding pending
**Implemented:** shared real-model agent, signed OIDC identity at gateway and
backends, per-domain claim enforcement, demo writes/approvals disabled,
private loopback interfaces, pinned app revisions, synthetic golden cases and
runbooks.
**Unverified:** actual IdP provisioned and connected, real signed-token
end-to-end handshake, evaluation sample scores, domain owner acceptance,
data processing/security approval and operational on-call.
**Promotion requires:** validated user roles and scoped records, stakeholder
evaluation, authorized IdP and TLS ingress, reviewed privacy policy and
measured cost/quality/latency. Synthetic-only testing until approved.

## Production — hardened code baseline, NOT released for real business traffic
**Implemented:** the same signed OIDC read-only gateway/backend path,
fail-closed demo mutations, service sandboxing, secrets separation, EC2 instance
profile template, monitoring and release regression gates.
**Unverified and/or not implemented:** user-specific record-level entitlements,
token-bound service-to-service identity beyond shared backend secret, managed
HA database, tamper-evident audit, multi-node scaling, secure real-data
connectors, disaster recovery tests, penetration/security reviews, active
CloudWatch alert notifications, SLO dashboard/alert ownership and change
approval. The sample EC2 single-host design is **NOT** high availability.
**Release gate:** do not use real customer information, expose a public API or
call this production-operational until all missing controls and signoffs are
implemented, tested and approved.

## Verification commands (using a virtual environment with test dependencies)
```bash
git fetch origin
git switch poc  # or pilot / production
git pull --ff-only origin $(git branch --show-current)
bash scripts/clone_business_apps.sh
bash scripts/sync_business_versions.sh  # explicit confirmation, clean checkouts only
bash scripts/verify_business_versions.sh
python -m unittest discover -s tests -p test_asr_agent.py -v
python -m unittest discover -s tests -p test_oidc_crypto.py -v
python -m unittest discover -s tests -p test_oidc_stage.py -v
python -m unittest discover -s tests -p test_release_guard.py -v
python -m unittest discover -s tests -p test_asr_evaluation.py -v
python scripts/smoke_integration.py
```
CI will also test an isolated four-service smoke stack. Without a recorded
successful CI run and live Bedrock evidence, these are **implemented checks**,
not observed passing results.

## AWS operator steps
Review `infrastructure/README.md`, the CloudFormation costs and permissions,
configure `.env.business`, then use `infrastructure/install-systemd.sh` on
an authorized Ubuntu EC2 machine. Verify root-controlled secrets and SSH
localhost tunnels. No new AWS resources have been provisioned by this code
review. Do not run a second EC2 launch if one already exists.

## Release governance
Use reviewed changes and pinned artifacts for promotion. The branch names
reflect intended maturity and differ in their enforced stage markers. A merge
is not equivalent to a pilot/production signoff. Keep source data synthetic
until legal, security, privacy and business operators formally authorize
a real environment.
