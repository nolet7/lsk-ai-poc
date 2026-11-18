variable "aws_region" {
  type        = string
  description = "Workload region; organization SCP permits Ohio for this lab."
  default     = "us-east-2"
  validation {
    condition     = var.aws_region == "us-east-2"
    error_message = "This development module is restricted to us-east-2."
  }
}
variable "aws_profile" {
  type        = string
  description = "Member-account Identity Center profile."
  default     = "lsk-development"
}
variable "expected_account_id" {
  type        = string
  description = "Required target member account ID, supplied at runtime; never commit identifiers."
  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "Provide the approved 12-digit development AWS account ID."
  }
}
variable "owner_tag" {
  type        = string
  description = "Non-sensitive cost owner."
  default     = "lsk-ai-platform"
}
variable "vpc_cidr" {
  type        = string
  default     = "10.42.0.0/16"
}
variable "enable_internet_gateway" {
  type        = bool
  default     = false
  description = "Explicit opt-in to public 0.0.0.0/0 routing; no NAT is created."
}
