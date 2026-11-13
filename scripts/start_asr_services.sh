#!/usr/bin/env bash
# Start four independent FastAPI services WITHOUT Docker; local or Ubuntu EC2.
# Bind to localhost only. For production readiness, replace with systemd + IAM role.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env.business}"
VENV="${ASR_VENV:-$ROOT/.venv-asr}"
RUN_DIR="$ROOT/.run-asr"

[[ -f "$ENV_FILE" ]] || { echo "Missing .env.business. Copy .env.business.example, fill in both keys, then rerun." >&2; exit 1; }
# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a
# Stage comes from this branch's committed marker, not an untrusted caller flag.
# Only POC may permit demo mutations.
source "$ROOT/integrations/release-stage.env"
export LSK_STAGE
[[ -n "${DEMO_API_KEY:-}" && -n "${GATEWAY_API_KEY:-}" ]] || { echo "Set both API keys in .env.business" >&2; exit 1; }
[[ "$DEMO_API_KEY" != replace-* && "$GATEWAY_API_KEY" != replace-* ]] || { echo "Replace sample keys before starting" >&2; exit 1; }

for repo in lsk-sales-account lsk-marketing lsk-finance; do
  [[ -f "$ROOT/external/$repo/app/main.py" ]] || { echo "Clone missing $repo using bash scripts/clone_business_apps.sh" >&2; exit 1; }
done
if [[ "$LSK_STAGE" == "pilot" || "$LSK_STAGE" == "production" ]]; then
  bash "$ROOT/scripts/verify_business_versions.sh"
fi
command -v python3 >/dev/null && PY=python3 || PY=python
if [[ ! -x "$VENV/bin/python" && ! -x "$VENV/Scripts/python.exe" ]]; then
  "$PY" -m venv "$VENV"
fi
if [[ -x "$VENV/bin/python" ]]; then
  VENV_PYTHON="$VENV/bin/python"
else
  VENV_PYTHON="$VENV/Scripts/python.exe"
fi
"$VENV_PYTHON" -m pip install -q "fastapi>=0.115,<1" "uvicorn>=0.30,<1" "httpx>=0.27,<1" "langgraph>=1,<2" "prometheus-client>=0.20,<1" "PyJWT[crypto]>=2.9,<3" "boto3>=1.35,<2"
mkdir -p "$RUN_DIR"
export SALES_SERVICE_URL="http://127.0.0.1:8101"
export MARKETING_SERVICE_URL="http://127.0.0.1:8102"
export FINANCE_SERVICE_URL="http://127.0.0.1:8103"
export AWS_REGION="${AWS_REGION:-us-east-1}"

start() {
  local name="$1" path="$2" port="$3" domain="$4"
  local pidfile="$RUN_DIR/$name.pid"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name is already running (pid $(cat "$pidfile")); not starting a duplicate."
    return
  fi
  (export APP_DOMAIN="$domain"; cd "$path" && exec "$VENV_PYTHON" -m uvicorn "$([[ "$name" == gateway ]] && echo 'integrations.gateway:app' || echo 'app.main:app')" --host 127.0.0.1 --port "$port") > "$RUN_DIR/$name.log" 2>&1 &
  echo "$!" > "$pidfile"
  echo "Started $name on 127.0.0.1:$port (pid $(cat "$pidfile"))"
}
# The subprocess environment must set APP_DOMAIN before each launch. All three
# services use independent SQLite databases because they run from separate cwd.
start sales "$ROOT/external/lsk-sales-account" 8101 sales
start marketing "$ROOT/external/lsk-marketing" 8102 marketing
start finance "$ROOT/external/lsk-finance" 8103 finance
start gateway "$ROOT" 8090 gateway
echo "Check: curl http://127.0.0.1:8090/health"
echo "Logs: $RUN_DIR/*.log"
echo "Model mode: BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID:+configured}; without it /v1/agent/run responds 503."
echo "To stop: bash scripts/stop_asr_services.sh"
