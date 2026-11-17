# TASK 01 — AWS identity, workstation tools and cost controls

**Status:** READY — FIRST TASK. **No paid AWS infrastructure is deployed in this task.** Run commands locally on Windows PowerShell, not inside EC2.

## Learning outcomes
Understand AWS CLI identity, least-privilege access, Terraform initialization, provider pinning, budgets, environment boundaries and what is safe to share for an engineering review.

## Prerequisites
An AWS account or approved training subaccount with AWS CLI v2 access via IAM Identity Center (preferred) or another short-lived role session. Terraform CLI >= 1.11.0. Git. Optional: VS Code Terraform extension. Do not create IAM long-lived access keys just for this lab.

## Actions
1. Clone/open the branch:
```powershell
git clone --branch feature/aws-enterprise-terraform https://github.com/nolet7/lsk-ai-poc.git
cd lsk-ai-poc
git branch --show-current
```
2. Install AWS CLI v2 and Terraform CLI from official sources. Verify:
```powershell
aws --version
terraform version
git --version
```
3. Configure an AWS SSO profile using `aws configure sso --profile lsk-lab`, log in via `aws sso login --profile lsk-lab`, and select a workload/nonproduction account and region. If your organization doesn't use IAM Identity Center, use its approved temporary/assumed-role method. **Do not paste any secret key, SSO code or token.**
4. Confirm identity:
```powershell
aws sts get-caller-identity --profile lsk-lab
aws configure get region --profile lsk-lab
```
The account ID and ARN are sensitive organization metadata: redact them before sharing. Do not proceed if account/role does not match intended nonproduction.
5. In AWS Billing & Cost Management, set AWS Budgets email alert(s) with a small lab-specific amount. Verify any account policy for EKS, NAT, Aurora, Bedrock and resource cleanup. AWS Budgets alerts are not a hard spending cap. Identify who is authorized to approve billable provisioning.
6. Inspect `deploy/aws/enterprise/ARCHITECTURE.md` and `README.md`. Explain in your own words why private EKS nodes and Aurora should not have public IPs; identify the first billable resource in the roadmap.
7. Validate Terraform source without provisioning:
```powershell
cd deploy/aws/enterprise/terraform/bootstrap
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```
`init -backend=false` downloads provider dependencies but no AWS infrastructure; networking is needed to download the provider. Review lockfile changes if generated; keep the lockfile in source control eventually. **Do not run terraform apply in Task 01.**

## Evidence to provide for review
- Branch name, OS, AWS CLI version and Terraform version.
- Redacted summary of `aws sts get-caller-identity` confirming intended nonproduction account + role (no full IDs).
- Region selected and confirmation budget alert was configured (no personal email needed).
- Output of `terraform fmt -check -recursive` and `terraform validate` (pass/fail and errors).
- A two-sentence explanation of why application and data subnets remain private.

## Acceptance criteria
- [ ] Correct project branch
- [ ] Working, authorized temporary AWS credentials
- [ ] Verified nonproduction account and selected region
- [ ] Budget notifications configured; explicit agreement no automatic apply
- [ ] Terraform source format/validation clean
- [ ] Network isolation understood

## Failure modes
- `aws: command not found`: install CLI and open a new terminal.
- `terraform: command not found`: install Terraform and update PATH.
- AWS 403: request appropriate scoped permissions from account administrator; never switch to AdministratorAccess as a shortcut.
- Provider download errors: check corporate proxy, Terraform registry access and local firewall.
- Terraform format mismatch: run `terraform fmt -recursive`, review diff, commit only intentional edits.

**Stop here. Send the evidence for review. Do not execute Task 02 until Task 01 passes.**
