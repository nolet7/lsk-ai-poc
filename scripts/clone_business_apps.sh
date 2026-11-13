#!/usr/bin/env bash
set -euo pipefail
mkdir -p external
for name in lsk-sales-account lsk-marketing lsk-finance; do
  if [ -d "external/$name/.git" ]; then
    echo "Found existing clone: external/$name (not overwriting local changes)"
  else
    git clone "https://github.com/nolet7/$name.git" "external/$name"
  fi
done
echo "Next: copy .env.business.example to .env.business, set keys, then run docker compose --env-file .env.business -f compose.business.yml up --build"
