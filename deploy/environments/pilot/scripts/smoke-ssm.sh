#!/usr/bin/env bash
# Requires AWS CLI Session Manager plugin; no public HTTP/SSH opened.
set -euo pipefail
: "${INSTANCE_ID:?Set INSTANCE_ID=i-...}"
aws ssm start-session --target "$INSTANCE_ID" --profile "${AWS_PROFILE:-lsk-development}" \
 --region "${AWS_REGION:-us-east-2}" --document-name AWS-StartPortForwardingSession \
 --parameters '{"portNumber":["8081"],"localPortNumber":["18081"]}'
