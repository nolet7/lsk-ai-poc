#!/usr/bin/env bash
# Install four systemd services on Ubuntu 24.04 EC2. NO Docker.
# Must run from an already-reviewed, pinned checkout of lsk-ai-poc.
set -euo pipefail
[[ "$(id -u)" -ne 0 ]] || { echo "Run as an Ubuntu user with sudo, not root." >&2; exit 1; }
command -v sudo >/dev/null || { echo "sudo required" >&2; exit 1; }
command -v rsync >/dev/null || { echo "Install rsync: sudo apt install rsync" >&2; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/integrations/release-stage.env"
[[ "$LSK_STAGE" =~ ^(poc|pilot|production)$ ]] || { echo "Invalid release stage"; exit 1; }
[[ -f "$ROOT/.env.business" ]] || { echo "Create .env.business with strong demo service secrets and stage-specific OIDC config"; exit 1; }
bash "$ROOT/scripts/verify_business_versions.sh"
set -a
# shellcheck disable=SC1090
source "$ROOT/.env.business"
set +a
[[ -n "${DEMO_API_KEY:-}" && -n "${GATEWAY_API_KEY:-}" ]] || { echo "Missing API keys" >&2; exit 1; }
[[ "$DEMO_API_KEY" != replace-* && "$GATEWAY_API_KEY" != replace-* ]] || { echo "Replace example credentials before installation" >&2; exit 1; }
if [[ "$LSK_STAGE" != poc ]]; then
  for field in BEDROCK_MODEL_ID OIDC_ISSUER OIDC_AUDIENCE OIDC_JWKS_URL METRICS_API_KEY; do
    [[ -n "${!field:-}" ]] || { echo "Missing required staged setting: $field" >&2; exit 1; }
  done
fi
echo "Installing stage '$LSK_STAGE' as loopback-only services; AWS role is required for real inference."
read -r -p "Type INSTALL to modify systemd and /opt/lsk-ai-poc: " consent
[[ "$consent" == "INSTALL" ]] || { echo "Cancelled"; exit 0; }
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip rsync
if ! id lskai >/dev/null 2>&1; then
  sudo useradd --system --home-dir /var/lib/lsk-ai --shell /usr/sbin/nologin lskai
fi
sudo install -d -m 0755 /opt/lsk-ai-poc
sudo install -d -m 0700 /etc/lsk-ai
for domain in sales marketing finance; do
  sudo install -d -o lskai -g lskai -m 0700 "/var/lib/lsk-ai/$domain"
done
# Never copy the developer's Git credentials, AWS CLI files, local .env, databases or generated data.
sudo rsync -a --exclude=.git --exclude=.env --exclude=.env.business \
  --exclude=config.env --exclude=.run-asr --exclude=.venv-asr \
  --exclude='*.sqlite3' --exclude=__pycache__ \
  --exclude=data/chroma_db --exclude=data/outputs \
  "$ROOT/" /opt/lsk-ai-poc/
sudo chown -R root:root /opt/lsk-ai-poc
sudo install -o root -g root -m 0600 "$ROOT/.env.business" /etc/lsk-ai/common.env
sudo install -o root -g root -m 0600 "$ROOT/integrations/release-stage.env" /etc/lsk-ai/stage.env
if [[ ! -x /opt/lsk-ai-poc/.venv-asr/bin/python ]]; then
  sudo python3 -m venv /opt/lsk-ai-poc/.venv-asr
fi
sudo /opt/lsk-ai-poc/.venv-asr/bin/python -m pip install \
  "fastapi>=0.115,<1" "uvicorn>=0.30,<1" "httpx>=0.27,<1" \
  "langgraph>=1,<2" "boto3>=1.35,<2" "prometheus-client>=0.20,<1" \
  "PyJWT[crypto]>=2.9,<3"
for name in sales marketing finance gateway; do
  sudo install -o root -g root -m 0644 \
    "$ROOT/infrastructure/systemd/lsk-$name.service" "/etc/systemd/system/lsk-$name.service"
done
sudo systemctl daemon-reload
for name in sales marketing finance gateway; do
  sudo systemctl enable --now "lsk-$name.service"
done
for name in sales marketing finance gateway; do
  sudo systemctl --no-pager --full status "lsk-$name.service" | head -n 12 || true
done
echo "Gateway bound to 127.0.0.1:8090; inspect with curl http://127.0.0.1:8090/health"
echo "Review logs: sudo journalctl -u lsk-gateway -n 100 --no-pager"
echo "No guarantee of live Bedrock inference or verified identity: run acceptance tests."
