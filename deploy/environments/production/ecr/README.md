# ECR bootstrap and narrowly scoped GitHub publisher

Separate Terraform state from ECS; create an immutable ECR repository plus a narrowly scoped GitHub Actions OIDC publisher role.

## Prerequisites
- Existing, approved GitHub Actions OIDC provider ARN in the same AWS account.
- Organization-managed private encrypted S3 state bucket and explicit IAM permissions.
- Configure GitHub protected environment `production-image-publish` with required reviewers and branch restriction. The IAM OIDC trust is scoped to the **environment name**, so environment protections are essential.
- IAM permission to create only the publisher role and ECR repo.

## Steps
```bash
cd deploy/environments/production/ecr
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
# Fill real values; review cost and permissions, set enabled=true after approval
terraform init -backend-config=backend.hcl
terraform fmt -check
terraform validate
terraform plan -out=reviewed.tfplan
# Apply reviewed.tfplan only after sign-off
```

Configure GitHub environment variables: `LSK_ECR_PUBLISH_ROLE_ARN` from Terraform output and `LSK_ECR_REPOSITORY=lsk-phase28-ai`. Then manually trigger `.github/workflows/fde-publish-production-image.yml`. Review image scanning results and pin `@sha256:...` in the ECS stack. No GitHub workflow auto-creates AWS infrastructure.
