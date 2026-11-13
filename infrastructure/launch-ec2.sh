#!/usr/bin/env bash
# Launch one Ubuntu EC2 host for the LSK POC. Run from Git Bash on Windows.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${CONFIG:-$HERE/config.env}"
if [[ ! -f "$CONFIG" ]]; then
  echo "Missing $CONFIG. Run: cp infrastructure/config.env.example infrastructure/config.env" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$CONFIG"
set +a

for cmd in aws; do command -v "$cmd" >/dev/null || { echo "Missing command: $cmd" >&2; exit 1; }; done
for variable in AWS_REGION AMI_ID INSTANCE_TYPE SUBNET_ID SG_ID KEY_NAME INSTANCE_NAME VOLUME_GIB; do
  [[ -n "${!variable:-}" ]] || { echo "Missing configuration: $variable" >&2; exit 1; }
done

echo "AWS caller:"
aws sts get-caller-identity --query '{Account:Account,Arn:Arn}' --output table
echo "Checking for existing EC2 instances tagged $INSTANCE_NAME ..."
# Includes stopped instances to prevent duplicate charges / unintended relaunches.
existing="$(aws ec2 describe-instances --region "$AWS_REGION" \
  --filters "Name=tag:Name,Values=$INSTANCE_NAME" \
    "Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down" \
  --query 'Reservations[].Instances[].InstanceId' --output text)"
if [[ -n "$existing" && "$existing" != "None" ]]; then
  echo "Existing instance(s): $existing"
  echo "Not launching another. Run: bash infrastructure/status-ec2.sh"
  exit 0
fi

echo "Validating image and network ..."
owner="$(aws ec2 describe-images --region "$AWS_REGION" --image-ids "$AMI_ID" --query 'Images[0].OwnerId' --output text)"
state="$(aws ec2 describe-images --region "$AWS_REGION" --image-ids "$AMI_ID" --query 'Images[0].State' --output text)"
arch="$(aws ec2 describe-images --region "$AWS_REGION" --image-ids "$AMI_ID" --query 'Images[0].Architecture' --output text)"
root="$(aws ec2 describe-images --region "$AWS_REGION" --image-ids "$AMI_ID" --query 'Images[0].RootDeviceName' --output text)"
[[ "$owner" == "099720109477" && "$state" == "available" && "$arch" == "x86_64" && -n "$root" && "$root" != "None" ]] || {
  echo "AMI validation failed: owner=$owner state=$state arch=$arch root=$root" >&2; exit 1;
}
aws ec2 describe-key-pairs --region "$AWS_REGION" --key-names "$KEY_NAME" --query 'KeyPairs[0].KeyName' --output text
aws ec2 describe-security-groups --region "$AWS_REGION" --group-ids "$SG_ID" --query 'SecurityGroups[0].GroupId' --output text
aws ec2 describe-subnets --region "$AWS_REGION" --subnet-ids "$SUBNET_ID" --query 'Subnets[0].SubnetId' --output text

echo
echo "About to LAUNCH a BILLABLE EC2 instance:"
printf '  Region: %s\n  Name: %s\n  Type: %s\n  AMI: %s\n  Storage: %s GiB gp3\n' \
 "$AWS_REGION" "$INSTANCE_NAME" "$INSTANCE_TYPE" "$AMI_ID" "$VOLUME_GIB"
echo "  This may also incur EBS and public IPv4 charges. Verify your AWS credits and budget."
read -r -p "Type LAUNCH to continue: " approval
[[ "$approval" == "LAUNCH" ]] || { echo "Cancelled."; exit 0; }

# Re-check after manual approval to reduce chance of accidental repeat runs.
existing="$(aws ec2 describe-instances --region "$AWS_REGION" \
  --filters "Name=tag:Name,Values=$INSTANCE_NAME" \
    "Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down" \
  --query 'Reservations[].Instances[].InstanceId' --output text)"
[[ -z "$existing" || "$existing" == "None" ]] || { echo "Found existing instance: $existing; aborting."; exit 1; }

# Unique CLI token makes a retry of this invocation idempotent (if repeated within AWS token retention).
token="lsk-ai-poc-$(date +%Y%m%d%H%M%S)-$$"
instance_id="$(aws ec2 run-instances \
  --region "$AWS_REGION" --client-token "$token" \
  --image-id "$AMI_ID" --instance-type "$INSTANCE_TYPE" --key-name "$KEY_NAME" \
  --network-interfaces "DeviceIndex=0,SubnetId=$SUBNET_ID,Groups=$SG_ID,AssociatePublicIpAddress=true" \
  --block-device-mappings "DeviceName=$root,Ebs={VolumeSize=$VOLUME_GIB,VolumeType=gp3,DeleteOnTermination=true,Encrypted=true}" \
  --metadata-options HttpTokens=required,HttpEndpoint=enabled \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME},{Key=Environment,Value=poc}]" \
  --query 'Instances[0].InstanceId' --output text)"
[[ "$instance_id" == i-* ]] || { echo "Unexpected instance ID: $instance_id" >&2; exit 1; }
echo "Created instance: $instance_id"
echo "Waiting for running state ..."
aws ec2 wait instance-running --region "$AWS_REGION" --instance-ids "$instance_id"
aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$instance_id" \
  --query 'Reservations[0].Instances[0].{ID:InstanceId,State:State.Name,PublicIP:PublicIpAddress,Type:InstanceType}' --output table
echo "Connect: ssh -i ~/.ssh/lsk-ai-poc ubuntu@<PublicIP> (verify SSH host fingerprint first)"
