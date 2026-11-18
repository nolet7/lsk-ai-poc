# Phase 28 — P28-08 Offline Integration Tests

These files replace the obsolete skipped adapter test and add a full in-process test across authorization, retrieval, grounding, budget reservation, and mocked Converse.

**No live AWS inference:** All Converse invocations use `unittest.mock.Mock`. Explicit `AISettings` flags are set inside the test fixture only.

## From repository root

```bash
python -m py_compile phase28/tests/test_bedrock_adapter.py phase28/tests/test_end_to_end.py
python -m unittest discover -s phase28/tests -p 'test_bedrock_adapter.py' -v
python -m unittest discover -s phase28/tests -p 'test_end_to_end.py' -v
python -m unittest discover -s phase28/tests -v
```

Expected: 5 replacement adapter tests and 8 integration tests, with the previous skipped adapter placeholder removed. Prior full suite had 65 discovered tests with one skipped. New suite should discover **77 tests**, provided nothing else has changed, and zero skips.

## Limitations

- This integration uses `InMemoryInferenceBudget`, not the persistent quota ledger. It does **not** validate crash recovery or cross-process request accounting in the service path.
- The mock token estimator is **not** a safe upper bound for live AWS calls.
- Model-generated citation IDs are mocked, so this does not establish factual entailment or prompt-injection resilience.
- No real gateway authentication, API version-contract verification, tamper-proof audit sink, business connector, IAM role isolation, distributed quota store, or AWS network call is tested.
- `phase28/bedrock_adapter.py` remains a separate legacy placeholder; this milestone tests the implemented `bedrock_client.py` and `budgeted_adapter.py` path.

Do **not** enable live Bedrock inference based on these unit tests alone.
