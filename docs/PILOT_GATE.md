# Pilot stage — release gates

This branch is seeded from `poc` to preserve the working Sales demonstration. **It is not yet a validated pilot release.**

Before calling this a pilot:
- Replace shared API key and spoofable `X-Role` with signed OIDC/JWT authentication, scoped permissions and independent reviewer authorization.
- Validate business process through stakeholder discovery; appoint a business owner.
- Add labeled synthetic acceptance cases for grounded account briefs, prompt injection, policy enforcement and protected CRM writes.
- Add telemetry for task success, completion time, tokens/cost, exceptions and p95 latency.
- Run supervised user testing, collect feedback and compare measured baseline with AI-assisted workflow.
- Document incident escalation, owner training, support and rollback.
- Add safe API integration with a documented OAuth scope model before real CRM access.

Promotion: technical reviewer, business owner and security lead sign off based on documented evidence. Never claim adoption or user impact without actual study data.

See `docs/CTO_MANDATE.md` and `sales_enablement/FDE_DELIVERY.md`.
