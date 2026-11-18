variable "ci_mode" {
  type        = bool
  description = "Use OIDC management state role and cross-account deployment role; default false for local CLI."
  default     = false
}
variable "ci_deployment_role_arn" {
  type        = string
  description = "Pre-provisioned member-account role assumed by the Terraform provider in GitHub Actions."
  default     = ""
  validation {
    condition     = var.ci_deployment_role_arn == "" || can(regex("^arn:aws:iam::[0-9]{12}:role/.+", var.ci_deployment_role_arn))
    error_message = "Provide a valid IAM role ARN, or leave blank for local use."
  }
}
