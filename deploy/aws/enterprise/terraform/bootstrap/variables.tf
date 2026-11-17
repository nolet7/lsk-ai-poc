variable "aws_region" {
  type        = string
  description = "AWS region holding the Terraform remote-state bucket."
  default     = "us-east-1"
}
variable "state_bucket_name" {
  type        = string
  description = "Globally unique S3 name for Terraform state (lowercase)."
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.state_bucket_name))
    error_message = "Use 3-63 lowercase letters, numbers, dots, or hyphens, starting and ending alphanumeric."
  }
}
variable "owner_tag" {
  type        = string
  description = "Non-sensitive cost owner tag."
}
