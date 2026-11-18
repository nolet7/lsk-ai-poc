#!/usr/bin/env bash
# One-time, manually approved LSK synthetic POC EC2 launch.
# Uses current AWS_PROFILE; no IAM instance profile or public application ports.
set -euo pipefail

: "${AWS_PROFILE:?Set AWS_PROFILE=lsk-development}"
export AWS_REGION="${AWS_REGION:-us-east-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"

EXPECTED_ACCOUNT="179793764737"
VPC_ID="vpc-03e3fe9e3f4beb2d8"
AMI_ID="ami-0f530fabb22a61065"
INSTANCE_TYPE="${LSK_INSTANCE_TYPE:-t3.large}"
NAME="lsk-ai-dev-poc-01"
PREFIX="lsk-ai-dev-poc-01"
WORK_DIR="/c/terraform-work/lsk-ai-poc/ec2-lab"
KEY_FILE="$WORK_DIR/$PREFIX"
STATE_FILE="$WORK_DIR/instance.env"

if [[ "$AWS_REGION" != "us-east-2" ]]; then
  echo "ERROR: AWS_REGION must be us-east-2" >&2; exit 1
fi
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
if [[ "$ACCOUNT" != "$EXPECTED_ACCOUNT" ]]; then
  echo "ERROR: Wrong AWS account $ACCOUNT" >&2; exit 1
fi
if [[ -e "$STATE_FILE" ]]; then
  echo "ERROR: $STATE_FILE already exists; inspect the prior lab before deploying again." >&2; exit 1
fi
EXISTING="$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$NAME" "Name=instance-state-name,Values=pending,running,stopping,stopped" --query 'Reservations[].Instances[].InstanceId' --output text)"
if [[ -n "$EXISTING" ]]; then
  echo "ERROR: Existing EC2 lab instance found: $EXISTING. Do not duplicate." >&2; exit 1
fi
IP="$(curl -fsS https://checkip.amazonaws.com | tr -d '\r\n')"
if [[ ! "$IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
  echo "ERROR: Could not determine IPv4 address." >&2; exit 1
fi
SUBNET="$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0].SubnetId' --output text)"
[[ -n "$SUBNET" && "$SUBNET" != "None" ]] || { echo "ERROR: No subnet found"; exit 1; }
ROOT_DEVICE="$(aws ec2 describe-images --image-ids "$AMI_ID" --query 'Images[0].RootDeviceName' --output text)"
[[ "$ROOT_DEVICE" != "None" && -n "$ROOT_DEVICE" ]] || { echo "ERROR: AMI missing"; exit 1; }

printf '\nACCOUNT: %s\nREGION: %s\nAMI: %s\nINSTANCE: %s\nSUBNET: %s\nSSH ALLOWED FROM: %s/32\nROOT EBS: 30 GiB encrypted gp3; delete on termination\n\n' "$ACCOUNT" "$AWS_REGION" "$AMI_ID" "$INSTANCE_TYPE" "$SUBNET" "$IP"
echo "NOTE: EC2 compute, EBS and public IPv4 charges begin when launched."
read -r -p 'Type DEPLOY EC2 to create the paid lab instance: ' CONFIRM
[[ "$CONFIRM" == "DEPLOY EC2" ]] || { echo "Cancelled without creating resources."; exit 0; }

mkdir -p "$WORK_DIR"
chmod 700 "$WORK_DIR"
if [[ ! -e "$KEY_FILE" && ! -e "$KEY_FILE.pub" ]]; then
  ssh-keygen -q -t ed25519 -f "$KEY_FILE" -N "" -C "$PREFIX-ssh" 
  chmod 600 "$KEY_FILE"
fi
[[ -f "$KEY_FILE.pub" && -f "$KEY_FILE" ]] || { echo "ERROR: SSH keypair incomplete"; exit 1; }
if ! aws ec2 describe-key-pairs --key-names "$PREFIX" --query 'KeyPairs[0].KeyName' --output text >/dev/null 2>&1; then
  # AWS CLI may be Windows-native: use fileb:// plus cygpath for the local public key.
  aws ec2 import-key-pair --key-name "$PREFIX" --public-key-material "fileb://$(cygpath -w "$KEY_FILE.pub")" >/dev/null
fi
SG_ID="$(aws ec2 create-security-group --group-name "$PREFIX" --description 'Temporary LSK commercial AI POC: SSH from owner only' --vpc-id "$VPC_ID" --query GroupId --output text)"
aws ec2 create-tags --resources "$SG_ID" --tags "Key=Project,Value=lsk-ai-poc" "Key=Environment,Value=development" "Key=Name,Value=$PREFIX" >/dev/null
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 22 --cidr "$IP/32" >/dev/null
MAPPING="$(printf '[{"DeviceName":"%s","Ebs":{"VolumeSize":30,"VolumeType":"gp3","Encrypted":true,"DeleteOnTermination":true}}]' "$ROOT_DEVICE")"
INSTANCE_ID="$(aws ec2 run-instances \
  --image-id "$AMI_ID" --instance-type "$INSTANCE_TYPE" --key-name "$PREFIX" \
  --subnet-id "$SUBNET" --security-group-ids "$SG_ID" \
  --associate-public-ip-address \
  --metadata-options 'HttpTokens=required,HttpEndpoint=enabled' \
  --block-device-mappings "$MAPPING" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME},{Key=Project,Value=lsk-ai-poc},{Key=Environment,Value=development}]" \
  --count 1 --query 'Instances[0].InstanceId' --output text)"
printf 'INSTANCE_ID=%q\nSG_ID=%q\nKEY_NAME=%q\n' "$INSTANCE_ID" "$SG_ID" "$PREFIX" > "$STATE_FILE"
chmod 600 "$STATE_FILE"
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
PUBLIC_IP="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"
printf 'PUBLIC_IP=%q\n' "$PUBLIC_IP" >> "$STATE_FILE"
printf '\nLaunched: %s\nPublic IP (SSH only): %s\nState file: %s\nSSH key: %s\n' "$INSTANCE_ID" "$PUBLIC_IP" "$STATE_FILE" "$KEY_FILE"
echo "Next: transfer validated release via SCP, run bootstrap-from-release.sh, and open port forwarding."
echo "IMPORTANT: terminate after lab; run deploy/aws/ec2/terminate-lab.sh."
