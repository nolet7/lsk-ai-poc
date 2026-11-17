#!/usr/bin/env bash
# Safe smoke test: synthetic read endpoints and blocked unauthorized changes.
set -euo pipefail
cd "$(dirname "$0")/../../.."
[[ -f .env.business ]] || { echo "Missing .env.business"; exit 1; }
set -a
# shellcheck disable=SC1091
source .env.business
set +a
BASE="${BASE_URL:-http://127.0.0.1:8090}"
KEY="${GATEWAY_API_KEY:?GATEWAY_API_KEY missing}"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
echo "1. Health"
curl --fail --silent --show-error "$BASE/health" | jq -e '.status=="ok"'
echo "2. Authentication denies missing key"
status="$(curl -sS -o "$tmp" -w '%{http_code}' "$BASE/v1/apps" -H 'X-Actor: employee')"
[[ "$status" == "401" ]] || { echo "Expected 401, got $status"; cat "$tmp"; exit 1; }
echo "3. Real Sales/Marketing/Finance capability discovery"
curl --fail --silent --show-error "$BASE/v1/apps" -H "X-API-Key: $KEY" -H 'X-Actor: employee' |
  jq -e '(.sales.status=="available") and (.marketing.status=="available") and (.finance.status=="available")'
echo "4. Retrieval-only AI path: must use authorized synthetic documents"
curl --fail --silent --show-error -X POST "$BASE/v1/platform/ask" \
  -H "X-API-Key: $KEY" -H 'X-Actor: employee' -H 'Content-Type: application/json' \
  -d '{"question":"Explain the invoice exception review process.","domain":"finance","use_model":false}' |
  jq -e '.mode=="retrieval-only" and (.evidence.sources | length > 0) and (.actions_taken | length == 0)'
echo "5. Legacy mutation route must be blocked"
status="$(curl -sS -o "$tmp" -w '%{http_code}' -X POST "$BASE/v1/apps/finance/proposals" \
 -H "X-API-Key: $KEY" -H 'X-Actor: employee' -H 'Content-Type: application/json' \
 -d '{"record_id":"inv-1002","text":"Review invoice","reason":"synthetic discrepancy"}')"
[[ "$status" == "410" ]] || { echo "Expected 410, got $status"; cat "$tmp"; exit 1; }
echo "6. No model configured: model inference must fail closed (503)"
if [[ -z "${BEDROCK_MODEL_ID:-}" ]]; then
  status="$(curl -sS -o "$tmp" -w '%{http_code}' -X POST "$BASE/v1/platform/ask" \
   -H "X-API-Key: $KEY" -H 'X-Actor: employee' -H 'Content-Type: application/json' \
   -d '{"question":"Explain the invoice exception review process.","domain":"finance","use_model":true}')"
  [[ "$status" == "503" ]] || { echo "Expected 503, got $status"; cat "$tmp"; exit 1; }
else
  echo "SKIP: Bedrock model configured; validate separately and monitor cost"
fi
echo 'PASS: EC2 POC gateway, three services, ACL retrieval, negative authorization checks'
