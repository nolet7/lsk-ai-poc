# The state is in the MANAGEMENT account. The provider uses the
# DEVELOPMENT account profile (see versions.tf).
# Backend SSO and provider SSO are deliberately different.
terraform {
  backend "s3" {
    bucket       = "lsk-ai-platform-proj1asr"
    key          = "development/network/terraform.tfstate"
    region       = "us-east-1"
    profile      = "lsk-management"
    encrypt      = true
    use_lockfile = true
  }
}
