#!/usr/bin/env bash
# Terminate only the dedicated temporary LSK EC2 lab, then remove its SG and AWS key.
set -euo pipefail
: "${AWS_PROFILE:?Set AWS_PROFILE=lsk-development}"
export AWS_REGION="${AWS_REGION:-us-east-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"
[[ "$AWS_REGION" == "us-east-2" ]] || { echo "Wrong region"; exit 1; }
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
[[ "$ACCOUNT" == "179793764737" ]] || { echo "Wrong account"; exit 1; }
WORK_DIR="/c/terraform-work/lsk-ai-poc/ec2-lab"
STATE_FILE="$WORK_DIR/instance.env"
[[ -f "$STATE_FILE" ]] || { echo "State file not found: $STATE_FILE"; exit 1; }
# shellcheck disable=SC1090
source "$STATE_FILE"
: "${INSTANCE_ID:?}" "${SG_ID:?}" "${KEY_NAME:?}"
NAME="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query "Reservations[0].Instances[0].Tags[?Key=='Name'].Value|[0]" --output text)"
[[ "$NAME" == "lsk-ai-dev-poc-01" ]] || { echo "Instance name mismatch, refusing termination: $NAME"; exit 1; }
printf 'Terminating %s in account %s (30 GiB root EBS configured delete-on-termination).\n' "$INSTANCE_ID" "$ACCOUNT"
read -r -p 'Type TERMINATE EC2 to end the lab: ' CONFIRM
[[ "$CONFIRM" == "TERMINATE EC2" ]] || { echo "Cancelled."; exit 0; }
aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" >/dev/null
aws ec2 wait instance-terminated --instance-ids "$INSTANCE_ID"
aws ec2 delete-security-group --group-id "$SG_ID"
aws ec2 delete-key-pair --key-name "$KEY_NAME"
echo "PASS: instance terminated, project security group and AWS public key removed."
echo "Inspect EBS volumes, snapshots, costs and public IPv4 releases in AWS. Keep local private SSH key protected or securely delete it when no longer needed."
mv "$STATE_FILE" "$STATE_FILE.terminated"
