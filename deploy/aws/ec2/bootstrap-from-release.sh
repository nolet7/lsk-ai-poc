#!/usr/bin/env bash
# Boot a CI-created four-service release directory on Ubuntu 24.04 EC2.
# No GitHub token, git clone, or AWS credential is stored on the host.
set -euo pipefail
[[ "$(id -u)" -ne 0 ]] || { echo "Run as ubuntu, not root"; exit 1; }
cd "$(dirname "$0")/../../.."
for path in integrations/gateway.py external/lsk-sales-account/Dockerfile external/lsk-marketing/Dockerfile external/lsk-finance/Dockerfile compose.business.yml; do
  [[ -f "$path" ]] || { echo "Missing required release file: $path"; exit 1; }
done
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl jq openssl docker.io docker-compose-v2
sudo systemctl enable --now docker
if [[ ! -f .env.business ]]; then
  umask 077
  {
    printf 'GATEWAY_API_KEY=%s\n' "$(openssl rand -hex 32)"
    printf 'DEMO_API_KEY=%s\n' "$(openssl rand -hex 32)"
    printf 'LSK_ENABLE_DEMO_WRITES=false\n'
    printf 'AWS_REGION=us-east-2\n'
    printf 'BEDROCK_MODEL_ID=\n'
  } > .env.business
fi
chmod 600 .env.business
sudo docker compose --env-file .env.business -f compose.business.yml config --quiet
sudo docker compose --env-file .env.business -f compose.business.yml up --build -d
bash deploy/aws/ec2/smoke.sh
echo "PASS: Release running on loopback only. Access via AWS SSM port-forwarding; never open 8090/8101/8102/8103 to internet."
