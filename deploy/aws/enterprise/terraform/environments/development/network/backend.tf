# Shared management-account state bucket. Credentials are provided by:
# - local CLI: AWS_PROFILE=lsk-management during terraform init
# - GitHub Actions: management-account OIDC state-access role
# Workload provider credentials are independent (see versions.tf).
terraform {
  backend "s3" {
    bucket       = "lsk-ai-platform-proj1asr"
    key          = "development/network/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
