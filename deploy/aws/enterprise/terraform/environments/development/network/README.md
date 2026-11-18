# Development network — low-cost Terraform POC

**Status:** Code prepared for review, **NOT deployed**. This module only provisions a segregated 2-AZ VPC foundation after approval. It does NOT modify the existing AWS default VPC. See [Task 03](../../../tasks/03-network-foundation.md) and [deployment mentoring guide](../../../DEPLOYMENT_MAP_AND_ENGINEER_GUIDE.md).

## Why this implementation

- **Account boundary:** the `aws` provider uses `lsk-development` (existing Next Big Thing member account). A precondition checks an explicit expected account ID to prevent management-account workloads.
- **Different state authority:** the S3 **backend** uses `lsk-management` to read/write `development/network/terraform.tfstate` in the management account's existing encrypted, versioned S3 bucket, with `use_lockfile=true`. Backend permissions and workload permissions are intentionally distinct; test them.
- **Region:** workload API calls go to Ohio `us-east-2`. The management S3 backend stays in Virginia `us-east-1`; these are separate concerns. Explicit backend/provider profiles avoid the prior AWS_REGION shadowing problem.
- **Six subnets across two AZs:** public `10.42.0.0/24`, `10.42.1.0/24`; private app `10.42.10.0/24`, `10.42.11.0/24`; isolated data `10.42.20.0/24`, `10.42.21.0/24`.
- **No paid always-on infrastructure:** no NAT gateways, elastic IPs, ALB, EKS, Aurora, EC2 or chargeable endpoints. No internet gateway or default route unless explicitly enabled; all subnets disable auto public IPv4. VPC, subnet, route-table resources are generally not billed themselves, but associated traffic/services may incur costs.
- **No egress from private/data:** their route tables have local-only routes. Public tier also has local-only routing by default. This is a network skeleton, **not** a runnable internet-connected application environment.
- **POC vs production:** production needs reviewed 3-AZ architecture, per-AZ boundaries, ingress/egress choices, flow logs, SGs/network policies, operational monitoring and explicit cost approval.

## CLI-only preflight in Windows Git Bash

```bash
# First copy this directory from the checked-out Git branch to a protected
# non-OneDrive location, as done for bootstrap/account-vending.
cd /c/terraform-work/lsk-ai-poc/network
aws sso login --profile lsk-management
aws sso login --profile lsk-development
export AWS_REGION=us-east-2 AWS_DEFAULT_REGION=us-east-2 AWS_PROFILE=lsk-development
export TF_VAR_expected_account_id="$(aws sts get-caller-identity --profile lsk-development --query Account --output text)"
aws sts get-caller-identity --profile lsk-development
aws sts get-caller-identity --profile lsk-management
terraform fmt -check -recursive
terraform init
terraform validate
terraform plan -out=network.tfplan
terraform show network.tfplan
```

**Review before applying:** the plan should create only this project's VPC, six subnets, three route tables and six associations. With `enable_internet_gateway=false`, there is no IGW, NAT or route to `0.0.0.0/0`. If any unexpected AWS resource, wrong account/region, cost or destruction appears, STOP. Check IAM and organization SCP/RCP constraints, including policies inherited from the root. **Do not run apply until an authorized reviewer approves the plan**.

## After an explicitly approved apply

Verify `terraform plan -detailed-exitcode` is no-change; compare `terraform output` with `aws ec2 describe-vpcs`, `describe-subnets`, `describe-route-tables` using the development profile and `us-east-2`. Verify no automatic public IPv4 and no nonlocal default routes in private/data tier. Record cost and drift checks.

## Limitations

- This first lab deliberately uses shared private/data route tables, no security groups, flow logs, NAT, endpoints or workload deployments. Not production ready.
- The work is on the existing member account only while the new-account quota remains pending.
- Do not confuse the *management* S3 state location with the *member-account* workload target.
- `terraform.tfvars`, `*.tfplan`, state and secrets must remain uncommitted. Store any recovery copies securely outside OneDrive.
