#!/usr/bin/env bash
# Root-only installation from reviewed, prepopulated local wheelhouse.
set -euo pipefail
[[ "$EUID" == "0" && "$#" == 2 ]] || { echo 'Usage: sudo bash install-offline.sh /absolute/reviewed/checkout /absolute/wheelhouse' >&2; exit 2; }
CHECKOUT="$(realpath "$1")"
WHEELS="$(realpath "$2")"
[[ -d "$WHEELS" ]] || { echo "Missing wheelhouse" >&2; exit 2; }
export PIP_NO_INDEX=1
export PIP_FIND_LINKS="$WHEELS"
export PIP_DISABLE_PIP_VERSION_CHECK=1
bash "$CHECKOUT/deploy/aws/phase28_ec2/install-ai.sh" "$CHECKOUT"
echo 'Complete OIDC/RBAC/DB seed and service startup per README_DEPLOY_AI_AWS.md'
