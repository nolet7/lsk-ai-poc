variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS Organizations endpoint provider region; account itself is global."
}
variable "create_account" {
  type        = bool
  default     = false
  description = "Safety gate: Terraform plans no member account unless explicitly enabled."
}
variable "account_name" {
  type        = string
  default     = "LSK-AI-Development"
  description = "Display name for the new AWS member account."
}
variable "account_email" {
  type        = string
  default     = ""
  description = "Dedicated, unused contact email for the AWS member account; stored in Terraform state."
  sensitive   = true
}
variable "parent_ou_id" {
  type        = string
  default     = null
  nullable    = true
  description = "Optional existing approved Organizational Unit ID; do not auto-create one."
}
