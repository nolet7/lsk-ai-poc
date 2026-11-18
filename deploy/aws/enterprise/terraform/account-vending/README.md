# AWS Organizations Terraform account vending (protected root)

**Safe by default**: `create_account=false` provisions nothing. This is a reusable root for approved member account creation from the AWS Organizations **management account**. Do not apply using the `Next Big Thing` workload account or long-lived IAM user credentials.

## Why isolated root?
- AWS account provisioning is organization control-plane infrastructure, separate from account-local VPC/EKS/IAM modules and remote states.
- IAM Identity Center assignments, SCPs, Control Tower Account Factory integrations, budgets and logging are follow-up governed tasks; creating a member account **does not** grant its access to your currently configured SSO identity.
- Never automatically destroy an AWS account. `prevent_destroy=true`, `close_on_deletion=false` are intentional. Organization admin must explicitly handle retirement.
- Avoid creating root OU/policies from this module. Supply an existing reviewed `parent_ou_id` after account governance approval; if omitted, AWS uses the organization root.

## Preconditions — DO NOT SKIP
1. Check whether Control Tower Account Factory governs account creation. **If yes, use its approved account vending process instead** and do not apply this standalone resource.
2. Confirm `aws sts get-caller-identity` is an authorized **temporary assumed role in the organization management account**; a member-account SSO role is insufficient.
3. Read AWS Organizations SCPs, account creation quotas, unique account email requirements and policies for the management account. Your screenshot previously showed SCP restrictions in a member account. This module does not bypass them.
4. Configure budgets and central logging requirements; obtain approval for account creation. New accounts carry billing responsibility.
5. Terraform state contains the contact email and account inventory. Store state under authorized, encrypted, versioned **management account** S3 backend once established. This example intentionally has no backend block to avoid hardcoding a nonexistent bucket. Until backend is configured, do not apply from a synced OneDrive directory or another location where local state could be exposed.
6. The AWS provider may support `master_account_id` in `aws_organizations_organization` data. Confirm the installed provider version and schema during `terraform validate` and resolve before applying.

## Safe read-only inspection (Git Bash)
```bash
export AWS_PROFILE=YOUR_APPROVED_MANAGEMENT_SSO_PROFILE
aws sts get-caller-identity
aws organizations describe-organization --query 'Organization.{Id:Id,MasterAccountId:MasterAccountId,FeatureSet:FeatureSet}' --output json
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform plan
```
With default `create_account=false`, `terraform plan` must NOT show `aws_organizations_account` creation; the data sources may query Organizations. Check the account number in CLI output matches your management account (do not share unredacted output).

## Later, only after secure backend, identity, budget, email and approval gates
```bash
export AWS_PROFILE=YOUR_APPROVED_MANAGEMENT_SSO_PROFILE
export TF_VAR_account_email='DEDICATED_EMAIL_YOU_CONTROL'
export TF_VAR_create_account=true
# Optional: export TF_VAR_parent_ou_id='ou-...'
terraform plan -out=approved-account.tfplan
terraform show approved-account.tfplan
# Manual plan review and explicit authorized approval required before:
# terraform apply approved-account.tfplan
```
Terraform account creation may take time asynchronously. Never rerun or create duplicate accounts just because AWS still reports creation in progress.

## Evidence / gated next step
Provide redacted `aws sts get-caller-identity` and `aws organizations describe-organization`, proof of managed SSO session, cost/budget confirmation, governance/Control Tower check, `terraform validate` and the **no-create** default `terraform plan`. The reviewer must approve account creation separately. Do not paste emails, tokens, account numbers or state contents.
