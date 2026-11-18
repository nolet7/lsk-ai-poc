# Phase 28 — P28-02: Bedrock Converse client (learning exercise)

This package ONLY adds `phase28/bedrock_client.py` and `phase28/tests/test_bedrock_client.py`. Do not overwrite completed `phase28/config.py`.

**Acceptance criteria:** safe defaults block inference; no boto3 import/call required for offline tests; validate prompts, build Converse request correctly, parse results, reject malformed responses, and avoid logging secrets or user prompts.

**Critical safety requirement:** The mocked tests explicitly enable inference in memory but do not make AWS calls. Do not use live Bedrock calls until actual runtime rate limits, daily budgets, and token-cap checks have been integrated and independently validated. Configuration values alone do not enforce budgets.

From the Git repository root, run:

```bash
python -m unittest discover -s phase28/tests -p 'test_bedrock_client.py' -v
python -m unittest discover -s phase28/tests -p 'test_config.py' -v
```

The first suite initially fails as intended; fill in TODOs and rerun. Existing P28-01 tests should continue passing. Install boto3/botocore only when implementing the real-client factory. Never configure AWS credentials in source code.
