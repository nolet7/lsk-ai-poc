# LSK commercial AI — end-to-end operator walkthrough

**Scope:** Synthetic POC only. No real ERP writes, no true multi-tenant SSO, no approval execution. The six reference workloads in `docs/ARCHITECTURE_V2.md` are not all delivered by this one repository.

## 1. Local prerequisites

Run the repo from its root. The local Compose gateway and services listen on `127.0.0.1` only. AWS Bedrock is optional for retrieval-only tests.

```bash
bash scripts/clone_business_apps.sh
cp .env.business.example .env.business
# Set two different long random API keys in .env.business.
# Leave LSK_ENABLE_DEMO_WRITES=false for safe read-only testing.
docker compose --env-file .env.business -f compose.business.yml up --build -d
```

If existing external business checkouts have local modifications, the clone script preserves them. Verify compatible service versions before deployment.

## 2. Make an authenticated read-only request

Set the same private key used in `.env.business`:

```bash
export GATEWAY_API_KEY='REPLACE_WITH_THE_KEY_FROM_ENV_FILE'
curl -fsS http://127.0.0.1:8090/health
curl -fsS -X POST http://127.0.0.1:8090/v1/platform/ask \
  -H "X-API-Key: $GATEWAY_API_KEY" -H "X-Actor: employee" \
  -H "Content-Type: application/json" \
  -d '{"domain":"finance","question":"What is the process for reviewing an invoice exception?","use_model":false}'
```

Expected behavior: `mode=retrieval-only`, a cited synthetic document ID, and no model invocation. The document was ACL-checked **before** context was returned.

## 3. Ask the model using real synthetic evidence

Set an approved `BEDROCK_MODEL_ID` in the shell/environment of the gateway process, then restart it. The runtime needs an AWS IAM role or locally configured AWS credentials with narrowly scoped `bedrock:InvokeModel` permissions; check model availability, inference-profile requirements and costs first. Do not commit cloud credentials.

```bash
curl -sS -X POST http://127.0.0.1:8090/v1/platform/ask \
  -H "X-API-Key: $GATEWAY_API_KEY" -H "X-Actor: employee" \
  -H "Content-Type: application/json" \
  -d '{"domain":"finance","question":"Explain the invoice review rule and cite its source ID.","use_model":true}'
```

Expected result when Bedrock really runs: `mode=bedrock-converse`, `model`, `answer`, `sources`, and `usage`. If the model is not configured or fails, HTTP **503** is correct; the system must not fake an AI response.

For authoritative finance arithmetic, use `/v1/apps/finance/records/{record_id}/insight`. This route does not depend on the model.

## 4. Submit a synthetic, idempotent pending proposal

This is the **only** supported command demonstration and has no downstream write/approval. Do not enable it on a shared host.

```bash
# In isolated local POC only: set LSK_ENABLE_DEMO_WRITES=true in .env.business
# and restart the gateway container.
curl -sS -X POST http://127.0.0.1:8090/v1/platform/proposals \
  -H "X-API-Key: $GATEWAY_API_KEY" -H "X-Actor: employee" \
  -H "Idempotency-Key: demo-review-0001" \
  -H "Content-Type: application/json" \
  -d '{"domain":"finance","record_id":"inv-1002","text":"Review invoice variance","reason":"Synthetic invoice exception"}'
```

The response has `status=pending`, `proposal_id` and `replayed=false`. Sending the *same* request with the *same* idempotency key returns the same proposal with `replayed=true`; a different payload using that key returns HTTP **409**. There is no API to approve or execute these proposals in this module.

## 5. Test and stop

```bash
python -m unittest discover -s tests -p test_gateway_contract.py -v
python -m unittest discover -s tests -p test_enterprise_architecture.py -v
docker compose --env-file .env.business -f compose.business.yml down
```

Local state persists in volumes. For deliberate synthetic resets, review volumes before invoking any destructive Docker commands. Never treat this as production evidence.
