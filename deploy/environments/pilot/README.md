# Pilot — private EC2 + real Bedrock controlled rollout

**IaC added:** `terraform/` provisions an approved private EC2 instance, three interface endpoints (SSM, SSMMessages and Bedrock Runtime), optional S3 gateway endpoint, private security groups and encrypted gp3 volume. All resources are opt-in. No public IP or inbound application/SSH ports.

**Status:** infrastructure defined but NOT applied, and AI not verified running.

## Operator runbook
1. Configure SSO permission-set status `SUCCEEDED`, then run read-only `scripts/validate-preflight.sh`.
2. Use `scripts/bootstrap-iam.sh` with `AWS_PROFILE=lsk-development` to create only the scoped EC2 SSM role/profile. Requires the IAM permissions previously scoped to the role and profile. Existing roles should be reviewed before reuse. Authorized IAM administrator must attach the exact Bedrock/S3 permissions from `iam/bedrock-policy.template.json` after replacing placeholders.
3. Verify approved AMI contains SSM agent and Python venv; subnet route table and VPC DNS are correct. Current VPC has no NAT or public egress; prepare offline wheels and approved signed source artifact transfer before attempting pip.
4. From `terraform/`, copy `terraform.tfvars.example` to ignored `terraform.tfvars`. Run `terraform fmt -check`, `terraform init`, `terraform validate` and `terraform plan`. Review projected costs (interface endpoints billed hourly) and provider region. Set `enabled=true`, `approved_change=true` only after approval.
5. `terraform apply` creates networking and EC2, **not the AI installation**. Do not expose SSH/8081.
6. Transfer a full-SHA source checkout and offline wheelhouse using approved SSM/S3 mechanisms; follow `README_DEPLOY_AI_AWS.md`, and `deploy/aws/phase28_ec2/install-ai.sh`. Installer currently uses pip and needs approved dependency access; update install process for offline wheelhouse on isolated host.
7. Install JWKS/RBAC/operator env, initialize and seed synthetic data, start `lsk-phase28-ai` under systemd.
8. Use SSM port forwarding via `scripts/smoke-ssm.sh`, check `/health/ready`, signed JWT, access denial and retrieval-only.
9. Enable inference only after IAM/model/cost approval; preserve one sanitized sample response and the pilot rollback results.

## Restrictions
- No customer data or business writes.
- Single EC2/SQLite is not HA.
- No automatic JWKS rotation, distributed quotas or token-based USD budget.
- SSM port forwarding is for restricted operations, not enterprise user-facing ingress.
- Production target uses ECS Fargate + PostgreSQL, not this AMI.

See `docs/fde/RELEASE_GATES.md` for evidence required to promote.
