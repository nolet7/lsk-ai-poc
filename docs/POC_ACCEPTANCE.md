# POC technical acceptance — ASR commercial AI

**Independent synthetic portfolio simulation.** Do not use real ASR Group records.

## Automated local checks
```bash
git switch poc
git pull --ff-only origin poc
bash scripts/clone_business_apps.sh
bash scripts/verify_business_versions.sh
python -m unittest discover -s tests -p test_asr_agent.py -v
python -m unittest discover -s tests -p test_release_guard.py -v
python -m unittest discover -s tests -p test_operational_contract.py -v
```
Run in the venv with gateway dependencies installed. Existing local clones may not match pinned versions; the verifier does not modify them.

## Live model test (requires AWS model permission)
- Start the four synthetic services on loopback only and set the authorized `BEDROCK_MODEL_ID`.
- Call authenticated `GET /ready` to verify business API reachability and configured model identifier (does not prove IAM/model access).
- Call `POST /v1/agent/run` with `{"question":"Explain the discrepancy in synthetic invoice inv-1002 and cite the record ID."}`.
- Capture model identifier, `mode=bedrock-langgraph`, tool trace, successful record retrieval, final answer, response time and actual Bedrock invocation cost.
- Negative tests: malformed record, unsupported domain, missing model, API timeout, malicious note text, forbidden tool request, attempt to approve finance without reviewer credentials.
- Verify zero unauthorized writes; mark any failed case explicitly.

**Gate:** Do not promote until model tool use is demonstrated live, final output references verified records, latency and cost are measured, and negative tests pass.
