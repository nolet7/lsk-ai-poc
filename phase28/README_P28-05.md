# P28-05 — Offline persistent inference quota ledger

Creates `phase28/persistent_budget.py` and `phase28/tests/test_persistent_budget.py`.
This is a separate lab component; do **not** replace your existing P28-04 adapter or turn on live AWS inference.

## Installation
Copy the two files into the matching paths in your repository.

## Run
`python -m unittest discover -s phase28/tests -p 'test_persistent_budget.py' -v`
`python -m unittest discover -s phase28/tests -v`

## Design and safety restrictions
- SQLite uses transactions to serialize writes among processes on **one local host** using the same database file. Not a distributed quota service across Kubernetes nodes.
- Reservations are saved before any eventual model request; unresolved ones remain pending through restart.
- `settle(success=False)` preserves the full worst-case charge for uncertain outcomes.
- This module **does not** call Bedrock, construct boto3 clients, or accept AWS credentials.
- Existing `BudgetedBedrockAdapter` uses `InMemoryInferenceBudget`; this ledger is not yet wired to the adapter. Do not claim it enforces quotas for that adapter yet.
- Real-world implementation still needs: tenant isolation; centralized IAM/network route enforcement; trusted model-aware token preflight; store permissions and backups; credential handling; request idempotency; global atomic provider quota coordination; configuration/pricing version pinning; durable reconciliation, day rollover safeguards, and safe operation with retries/failures.
