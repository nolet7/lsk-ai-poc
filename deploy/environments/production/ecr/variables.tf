variable "enabled" {
  type = bool
  default = false
}
variable "aws_region" {
  type = string
  default = "us-east-2"
}
variable "repository_name" {
  type = string
  default = "lsk-phase28-ai"
}
variable "github_oidc_provider_arn" {
  type = string
  description = "ARN of an existing configured GitHub Actions OIDC provider in target account"
}
