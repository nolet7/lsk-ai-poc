#!/usr/bin/env bash
# Scoped development-account role/profile bootstrap, deliberately not adding Bedrock permissions.
set -euo pipefail
: "${AWS_PROFILE:?Set AWS_PROFILE=lsk-development}"
ACCOUNT="$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)"
[[ "$ACCOUNT" == "179793764737" ]] || { echo "Wrong AWS account" >&2; exit 2; }
ROLE="LSK-Phase28-EC2-Role"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if ! aws iam get-role --role-name "$ROLE" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
 aws iam create-role --role-name "$ROLE" --assume-role-policy-document "file://$ROOT/iam/ec2-trust.json" --profile "$AWS_PROFILE"
fi
aws iam attach-role-policy --role-name "$ROLE" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore --profile "$AWS_PROFILE"
if ! aws iam get-instance-profile --instance-profile-name "$ROLE" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
 aws iam create-instance-profile --instance-profile-name "$ROLE" --profile "$AWS_PROFILE"
fi
EXISTING="$(aws iam get-instance-profile --instance-profile-name "$ROLE" --profile "$AWS_PROFILE" --query 'InstanceProfile.Roles[].RoleName' --output text)"
if [[ -z "$EXISTING" ]]; then
 aws iam add-role-to-instance-profile --instance-profile-name "$ROLE" --role-name "$ROLE" --profile "$AWS_PROFILE"
elif [[ "$EXISTING" != "$ROLE" ]]; then
 echo "Instance profile associated with unexpected role: $EXISTING" >&2; exit 1
fi
echo "SSM instance role/profile prepared. Bedrock/S3 resource policy still requires approved administrator."
