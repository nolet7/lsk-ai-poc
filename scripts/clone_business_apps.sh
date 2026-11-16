#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/integrations/app-versions.env"
mkdir -p "$ROOT/external"
for entry in "lsk-sales-account:$SALES_COMMIT" "lsk-marketing:$MARKETING_COMMIT" "lsk-finance:$FINANCE_COMMIT"; do
  name="${entry%%:*}"
  commit="${entry#*:}"
  target="$ROOT/external/$name"
  if [[ -d "$target/.git" ]]; then
    echo "Preserving existing $name checkout; run scripts/verify_business_versions.sh to check exact revision."
  else
    git clone "https://github.com/nolet7/$name.git" "$target"
    git -C "$target" checkout --detach "$commit"
    echo "Cloned $name at pinned $commit"
  fi
done
echo "Configure .env.business and run Compose when all revisions verify."
