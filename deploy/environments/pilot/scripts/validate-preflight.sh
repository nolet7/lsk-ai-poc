#!/usr/bin/env bash
# Read-only AWS checks. Requires development SSO profile.
set -euo pipefail
PROFILE="${AWS_PROFILE:-lsk-development}"
REGION="${AWS_REGION:-us-east-2}"
VPC="${LSK_PILOT_VPC:-vpc-009da120ff1cddbf5}"
SUBNET="${LSK_PILOT_SUBNET:-subnet-054275fd09fd75d15}"
aws sts get-caller-identity --profile "$PROFILE"
aws ec2 describe-subnets --subnet-ids "$SUBNET" --region "$REGION" --profile "$PROFILE" \
 --query 'Subnets[].{ID:SubnetId,Vpc:VpcId,AZ:AvailabilityZone,PublicIP:MapPublicIpOnLaunch}' --output table
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC" --region "$REGION" --profile "$PROFILE" \
 --query 'VpcEndpoints[].{ID:VpcEndpointId,Service:ServiceName,State:State}' --output table
aws ssm describe-instance-information --region "$REGION" --profile "$PROFILE" \
 --query 'InstanceInformationList[].{ID:InstanceId,Status:PingStatus}' --output table
echo 'Review costs, SSO provisioning, IAM role/profile, private route tables and SSM permissions before enabling.'
