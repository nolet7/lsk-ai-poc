#!/usr/bin/env bash
# Ubuntu 24.04 EC2 bootstrap for the synthetic four-service POC.
set -euo pipefail
if [[ "$(id -u)" -eq 0 ]]; then echo "Run as ubuntu, not root"; exit 1; fi
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates git curl jq openssl docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
# sudo for Docker only: container membership is root-equivalent.
ROOT="${HOME}/lsk-ai-poc"
if [[ ! -d "$ROOT/.git" ]]; then
  git clone --branch feature/aws-ec2-poc-deploy https://github.com/nolet7/lsk-ai-poc.git "$ROOT"
fi
cd "$ROOT"
git fetch origin feature/aws-ec2-poc-deploy
git checkout feature/aws-ec2-poc-deploy
bash scripts/clone_business_apps.sh
bash scripts/verify_business_versions.sh
if [[ ! -f .env.business ]]; then
  umask 077
  {
    printf 'GATEWAY_API_KEY=%s\n' "$(openssl rand -hex 32)"
    printf 'DEMO_API_KEY=%s\n' "$(openssl rand -hex 32)"
    printf 'LSK_ENABLE_DEMO_WRITES=false\n'
    printf 'AWS_REGION=%s\n' "${AWS_REGION:-us-east-1}"
    printf 'BEDROCK_MODEL_ID=\n'
  } > .env.business
fi
chmod 600 .env.business
sudo docker compose --env-file .env.business -f compose.business.yml config --quiet
sudo docker compose --env-file .env.business -f compose.business.yml up --build -d
sudo docker compose --env-file .env.business -f compose.business.yml ps
printf '\nREADY for checks: bash deploy/aws/ec2/smoke.sh\n'
printf 'Connect from laptop with AWS Session Manager port forwarding; ports are bound to EC2 loopback only.\n'
