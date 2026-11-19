# Phase 28 / P28-11 — Offline governed deployment composition

This package adds `phase28/deployment.py` and `phase28/tests/test_deployment.py`. It does not change existing P28-01 through P28-10 files.

## Scope

- Fail closed before creating a Bedrock runtime client unless startup settings, persistent SQLite ledger, role identity probe, authorization, and audit dependencies are present.
- Validate externally obtained STS GetCallerIdentity Account and assumed-role ARN against an explicitly configured expected role. The identity probe is injected for testing and is **not itself trustworthy if supplied by a request**.
- Bind the approved runtime to `PersistentBudgetedBedrockAdapter`, and expose a read-only question-answering service rather than an unbudgeted model inference method.
- Parse model output as structured JSON; reject citations outside authorized evidence using existing service grounding validation.
- Run entirely offline with mocked identity and Converse calls. No boto3, AWS credentials, networking, Terraform deployment, or paid inference.

## Important limitations

This is **not production deployment validation**. AWS STS caller identity does not prove VPC endpoint usage, token estimator correctness, policy propagation, real model availability, or absence of other IAM permissions. Also, a `Principal` dataclass by itself is not a verified end-user JWT/OIDC identity; the deployment gateway must verify tokens before constructing one. The SQLite ledger is single-host. For multi-replica deployment, implement a transactional distributed quota ledger and idempotent operation key. Protect the raw runtime client in the composition root, enforce execution paths through IAM/network policy and code ownership, and validate endpoint policy + effective IAM role outside this offline lab. Evidence prompting also requires prompt-injection evaluation and secure factual entailment checking beyond ID validation.

## Run

```bash
python -m py_compile phase28/deployment.py phase28/tests/test_deployment.py
python -m unittest discover -s phase28/tests -p 'test_deployment.py' -v
python -m unittest discover -s phase28/tests -v
```

## Commit

```bash
git add phase28/deployment.py phase28/tests/test_deployment.py README_P28-11.md
git commit -m "feat(phase28): add governed deployment composition and identity checks"
git push origin feature/phase28-bedrock-ai-lab
```

**Do not enable real AWS inference based on these offline tests.**
