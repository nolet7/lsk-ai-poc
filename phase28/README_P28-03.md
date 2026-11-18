# P28-03 — Inference budget / quotas (offline)

## Files
- `phase28/budget.py`: complete single-process reference budget guard
- `phase28/tests/test_budget.py`: 9 offline unit tests

## Run from repo root
```bash
python -m unittest discover -s phase28/tests -v
```

## What the guard enforces
- Per-request input/output token ceilings before the call
- Rolling 60-second request allowance
- UTC daily request allowance
- Explicit model pricing supplied by the caller (USD per 1M tokens)
- Daily USD cap, reserving worst-case input + output spend first
- Atomic thread-safe reservation and settlement within one process
- Conservative charging of unknown/timeout outcomes

## Important operational boundaries
This does NOT enable real AWS inference. It is a local lab reference: no persistent
ledger, no multi-instance coordination, no AWS budget integration, no true provider
tokenization, no reconciliation with cloud bills, and no automatic cancellation.
Do not wire it into production requests without a durable centralized rate and
cost quota service and review of failure/rollover/idempotency semantics.

`AISettings` has no USD limit field; `max_daily_usd` must therefore be provided
explicitly at guard construction. The default model identifier is not evidence
that the model is enabled or available in your AWS account. Prices are *examples*
only in tests, not claims about AWS prices.

## Senior engineer follow-up tasks
1. Explain why reserving worst-case tokens is safer than charging after a call.
2. Add tests for concurrent requests, duplicate settlement, and day rollover.
3. Propose a Redis/DB-backed atomic ledger for multiple replicas.
4. Plan how to estimate prompt tokens before invoking Bedrock.
5. Plan how to reconcile `usage` with a model-dependent tokenizer and provider costs.
6. Keep real inference disabled until the centralized guard and explicit operator approval exist.
