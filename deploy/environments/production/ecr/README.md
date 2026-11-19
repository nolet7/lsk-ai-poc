# ECR bootstrap stack

Run **before** the production ECS stack. It is separate to avoid an image/repository deployment cycle. Create the ECR repository only after reviewing cost, registry and role permissions.

1. Copy `terraform.tfvars.example` to ignored `terraform.tfvars`; set `enabled=true` only after approval.
2. Configure protected encrypted Terraform state backend per organization rules.
3. `terraform init` / `terraform validate` / `terraform plan`; inspect changes and approve `terraform apply`.
4. Configure GitHub OIDC permission for the **repository and branch** to publish into this ECR repository. No long-lived AWS keys.
5. Trigger `.github/workflows/fde-publish-production-image.yml` explicitly; record image digest and scan findings. Promotion must use `@sha256:digest`, never only a mutable image tag.

No GitHub workflow here automatically creates AWS resources.
