#!/usr/bin/env bash
# Explicitly align existing clean business checkouts to the reviewed commit pins.
# Refuses dirty trees and requires operator confirmation. Does not delete data.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/integrations/app-versions.env"
for entry in "lsk-sales-account:$SALES_COMMIT" "lsk-marketing:$MARKETING_COMMIT" "lsk-finance:$FINANCE_COMMIT"; do
  name="${entry%%:*}"
  expected="${entry#*:}"
  dir="$ROOT/external/$name"
  if [[ ! -d "$dir/.git" ]]; then
    echo "$name is missing; use bash scripts/clone_business_apps.sh" >&2
    exit 1
  fi
  if [[ -n "$(git -C "$dir" status --porcelain)" ]]; then
    echo "$name has uncommitted changes; refusing to alter it." >&2
    exit 1
  fi
  current="$(git -C "$dir" rev-parse HEAD)"
  if [[ "$current" == "$expected" ]]; then
    echo "$name already matches expected $expected"
    continue
  fi
  echo "$name current=$current target=$expected"
  read -r -p "Type PIN to fetch and checkout exact pinned revision of $name: " confirmation
  [[ "$confirmation" == PIN ]] || { echo "Cancelled"; exit 1; }
  git -C "$dir" fetch origin "$expected"
  git -C "$dir" checkout --detach "$expected"
  echo "$name is now at $expected"
done
bash "$ROOT/scripts/verify_business_versions.sh"
