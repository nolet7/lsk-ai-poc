#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/integrations/app-versions.env"
for spec in "lsk-sales-account:$SALES_COMMIT" "lsk-marketing:$MARKETING_COMMIT" "lsk-finance:$FINANCE_COMMIT"; do
  name="${spec%%:*}"; expected="${spec#*:}"
  dir="$ROOT/external/$name"
  [[ -d "$dir/.git" ]] || { echo "MISSING $name; run bash scripts/clone_business_apps.sh" >&2; exit 1; }
  actual="$(git -C "$dir" rev-parse HEAD)"
  [[ "$actual" == "$expected" ]] || { echo "VERSION MISMATCH $name: actual=$actual expected=$expected" >&2; exit 1; }
  [[ -z "$(git -C "$dir" status --porcelain)" ]] || { echo "DIRTY checkout $name; commit or stash first" >&2; exit 1; }
  echo "OK $name $actual"
done
