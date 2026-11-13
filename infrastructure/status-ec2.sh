#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${CONFIG:-$HERE/config.env}"
[[ -f "$CONFIG" ]] || { echo "Missing $CONFIG; copy config.env.example first." >&2; exit 1; }
set -a
# shellcheck disable=SC1090
source "$CONFIG"
set +a
aws ec2 describe-instances --region "$AWS_REGION" \
  --filters "Name=tag:Name,Values=$INSTANCE_NAME" \
  --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name,Type:InstanceType,PublicIP:PublicIpAddress}' \
  --output table
