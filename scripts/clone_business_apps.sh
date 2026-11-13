#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/integrations/app-versions.env"
mkdir -p "$ROOT/external"
for spec in "lsk-sales-account:$SALES_COMMIT" "lsk-marketing:$MARKETING_COMMIT" "lsk-finance:$FINANCE_COMMIT"; do
  name="${spec%%:*}"; commit="${spec#*:}"
  dir="$ROOT/external/$name"
  if [[ -d "$dir/.git" ]]; then
    echo "Found existing $name: preserving user checkout. Run verify_business_versions.sh to compare pins."
  else
    git clone "https://github.com/nolet7/$name.git" "$dir"
    git -C "$dir" checkout --detach "$commit"
    echo "Checked out pinned $name revision $commit"
  fi
done
echo "Start without Docker: bash scripts/start_asr_services.sh (if installed on branch)."
