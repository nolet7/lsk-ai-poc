# TASK 02 — Bootstrap remote Terraform state and locking

**Status:** LOCKED until Task 01 review passes. Provisioning a state bucket may incur storage/request charges.

## Learning outcomes
Understand local bootstrap state, remote encrypted S3 state, native S3 lock files, least-privilege state management, and why Terraform state is sensitive.

## Exercise
1. Confirm AWS session/account/region. Request approval before any billable resource provisioning.
2. In `deploy/aws/enterprise/terraform/bootstrap`, copy `terraform.tfvars.example` to `terraform.tfvars` and choose a **globally unique** lowercase state bucket name. Do not commit `terraform.tfvars`. For an organization use central naming/cost conventions.
3. Run:
```powershell
$env:AWS_PROFILE="lsk-lab"
terraform fmt -check
terraform init
terraform validate
terraform plan -out=bootstrap.tfplan
terraform show bootstrap.tfplan
```
Review resources: versioned bucket, SSE-S3 encryption, TLS-only policy, blocked public access, bucket ownership controls, prevent_destroy. Validate plan has no surprise resources.
4. After plan approval:
```powershell
terraform apply bootstrap.tfplan
terraform output
```
5. Verify with AWS CLI (replace the literal placeholder with your bucket name; never paste account metadata unredacted):
```powershell
aws s3api get-bucket-versioning --bucket YOUR_BUCKET --profile lsk-lab
aws s3api get-public-access-block --bucket YOUR_BUCKET --profile lsk-lab
aws s3api get-bucket-encryption --bucket YOUR_BUCKET --profile lsk-lab
```
6. Design **separate** backend keys for `nonprod/network`, `nonprod/eks`, `nonprod/data`, and `prod/...` in separate authorized accounts. Future environment root example:
```hcl
terraform {
  backend "s3" {
    bucket       = "YOUR_BUCKET"
    key          = "nonprod/network/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
```
This is **illustrative** until the next task introduces the environment root; do not paste placeholders into an apply. Ensure IAM grants least-privilege state and lock-file operations. Terraform's S3-native `use_lockfile` is preferred over new DynamoDB locking.
7. Keep the bootstrap `terraform.tfstate` in a secured location, **not Git**. Plan eventual controlled migration and retention. Because `prevent_destroy` is set, do not use `terraform destroy` to clean up this foundational bucket.

## Evidence
Redacted reviewed plan counts, `terraform output`, versioning/encryption/public-access-block responses, and a brief explanation of S3 locking vs local state. Do not paste actual state, credentials or secrets.

## Acceptance
- [ ] Approved plan contains only expected bootstrap resources
- [ ] Apply successful in correct account
- [ ] S3 versioning enabled, encryption configured, all public access blocked, TLS policy installed
- [ ] Separate per-environment keys proposed
- [ ] State permissions reviewed; no state file or secrets committed

**Stop here and request review before beginning network provisioning.**
