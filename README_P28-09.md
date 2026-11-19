# Phase 28 — P28-09: Persistent-budget inference boundary (offline)

The new `phase28/persistent_adapter.py` is an **alternative** to the existing
`BudgetedBedrockAdapter`: it reserves in the existing P28-05 SQLite ledger
before invoking an injected Converse-compatible test runtime and reconciles
provider usage on success. On timeout, throttle, or malformed response, the
full worst-case charge is preserved. Over-reservation token usage remains
pending for manual reconciliation; requests are not automatically retried.

## Files

- `phase28/persistent_adapter.py` — implementation, no AWS credentials or SDK.
- `phase28/tests/test_persistent_adapter.py` — 11 offline tests.

## Execute at repository root

```bash
python -m py_compile phase28/persistent_adapter.py phase28/tests/test_persistent_adapter.py
python -m unittest discover -s phase28/tests -p 'test_persistent_adapter.py' -v
python -m unittest discover -s phase28/tests -v
```

Expected total assuming the prior 77 tests are unchanged: **88 tests**.

## Production restrictions

- **NO live AWS inference**. Flags `live_inference=True` in tests only gate an
  injected mock. No boto3 is initialized by this module.
- SQLite applies only to a **single host with one shared local database**.
  Kubernetes multi-node requires transactional, shared durable storage and
  documented tenant/model quota partitioning.
- The preflight `estimate_input_tokens` callback must be a **conservative,
  provider/model-aware upper bound**, not an arbitrary word/character estimate.
- Explicit `AISettings` identity is required between client, ledger and adapter.
- This does **not** implement IAM, AWS network policies, authenticating the
  gateway, per-tenant quotas, cross-replica coordination, audit persistence,
  idempotent retries, or proof of semantic factual grounding.
- An unexpected process termination between `reserve` and `settle` leaves a
  pending reservation: requires operator reconciliation. Do not arbitrarily
  refund unresolved provider outcomes.
- Pricing and settings consistency must be governed across ledger instances.
  The existing ledger does not version or pin its pricing configuration.
