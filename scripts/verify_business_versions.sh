#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/integrations/app-versions.env"
for entry in "lsk-sales-account:$SALES_COMMIT" "lsk-marketing:$MARKETING_COMMIT" "lsk-finance:$FINANCE_COMMIT"; do
  name="${entry%%:*}"
  expected="${entry#*:}"
  target="$ROOT/external/$name"
  [[ -d "$target/.git" ]] || { echo "MISSING: $name; clone first" >&2; exit 1; }
  actual="$(git -C "$target" rev-parse HEAD)"
  [[ "$actual" == "$expected" ]] || { echo "MISMATCH $name: expected $expected, got $actual" >&2; exit 1; }
  [[ -z "$(git -C "$target" status --porcelain)" ]] || { echo "DIRTY: $name; preserve changes before proceeding" >&2; exit 1; }
  echo "OK $name at $actual"
done
