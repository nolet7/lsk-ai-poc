variable "enabled" {
  description = "Explicitly opt into billable VPC endpoint and IAM resources"
  type        = bool
  default     = false
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
  validation {
    condition     = can(regex("^(us|eu|ap|ca|sa|me|af|il)-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "A concrete AWS region is required."
  }
}

variable "model_id" {
  type    = string
  default = "anthropic.claude-3-5-haiku-20241022-v1:0"
  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9._:+-]*$", var.model_id))
    error_message = "Only a foundation-model ID is supported (not ARN or inference profile)."
  }
}

variable "vpc_id" {
  type    = string
  default = ""
  validation {
    condition     = !var.enabled || can(regex("^vpc-[0-9a-f]{8,17}$", var.vpc_id))
    error_message = "When enabled, supply an existing VPC ID."
  }
}

variable "private_subnet_ids" {
  type    = list(string)
  default = []
  validation {
    condition     = !var.enabled || (length(var.private_subnet_ids) >= 1 && alltrue([for id in var.private_subnet_ids : can(regex("^subnet-[0-9a-f]{8,17}$", id))]))
    error_message = "When enabled, supply existing private subnet IDs."
  }
}

variable "application_security_group_id" {
  type    = string
  default = ""
  validation {
    condition     = !var.enabled || can(regex("^sg-[0-9a-f]{8,17}$", var.application_security_group_id))
    error_message = "When enabled, supply the application security group ID."
  }
}

variable "application_role_name" {
  type    = string
  default = ""
  validation {
    condition     = !var.enabled || (length(var.application_role_name) > 0 && length(var.application_role_name) <= 64 && can(regex("^[A-Za-z0-9+=,.@_-]+$", var.application_role_name)))
    error_message = "When enabled, supply the existing application role name."
  }
}

variable "application_role_arn" {
  type    = string
  default = ""
  validation {
    condition     = !var.enabled || can(regex("^arn:aws:iam::[0-9]{12}:role/.+$", var.application_role_arn))
    error_message = "When enabled, supply the existing application IAM role ARN."
  }
}
