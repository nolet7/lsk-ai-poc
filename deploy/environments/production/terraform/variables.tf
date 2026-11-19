variable "enabled" { 
  type = bool
  default = false
}
variable "approved_release" {
  type = bool
  default = false
}
variable "bootstrap_mode" {
  type = bool
  default = true
  description = "When true, create ECS service with zero tasks until DB migration is complete."
}
variable "aws_region" {
  type = string
  default = "us-east-2"
}
variable "vpc_id" { type = string }
variable "private_subnet_ids" {
  type = list(string)
  validation {
    condition = length(distinct(var.private_subnet_ids)) >= 2
    error_message = "At least two different private subnets are required."
  }
}
variable "private_route_table_ids" {
  type = list(string)
  validation {
    condition = length(var.private_route_table_ids) >= 1
    error_message = "Private route tables required for S3 gateway endpoint."
  }
}
variable "trusted_client_cidrs" {
  type = list(string)
  default = []
}
variable "alb_certificate_arn" {
  type = string
  description = "ACM certificate ARN for internal HTTPS listener"
}
variable "ecr_image_uri" {
  type = string
  description = "Immutable ECR image digest"
  validation {
    condition = can(regex("@sha256:[0-9a-f]{64}$", var.ecr_image_uri))
    error_message = "Require immutable ECR image digest ending in @sha256:64-hex."
  }
}
variable "db_name" {
  type = string
  default = "lskphase28"
}
variable "db_username" {
  type = string
  default = "lsk_admin"
}
variable "db_instance_class" {
  type = string
  default = "db.t4g.small"
}
variable "desired_tasks" {
  type = number
  default = 2
  validation {
    condition = var.desired_tasks >= 2
    error_message = "Non-bootstrap service needs at least two ECS tasks."
  }
}
variable "bedrock_model_arn" {
  type = string
  description = "Exact approved model or inference-profile ARN; verify Bedrock IAM requirements."
}
variable "bedrock_model_id" {
  type = string
  description = "Approved Converse model or inference profile ID"
}
variable "jwks_secret_arn" {
  type = string
  description = "Existing Secrets Manager ARN with PUBLIC trusted JWKS JSON"
}
variable "oidc_issuer" {
  type = string
  description = "Trusted HTTPS OIDC issuer, no trailing slash"
}
variable "oidc_audience" { type = string }
variable "rbac_json" {
  type = string
  default = "{\"reader\":[\"orders\"]}"
}
variable "max_daily_model_calls" {
  type = number
  default = 5
}
variable "live_inference_enabled" {
  type = bool
  default = false
}

variable "alarm_topic_arn" {
  type = string
  description = "Existing approved SNS alert topic ARN"
}

variable "enable_commercial_workflow" {
  type = bool
  default = false
  description = "Opt-in to separate authenticated MCP and LangGraph commercial path."
}
variable "mcp_resource_url" {
  type = string
  default = ""
  description = "Approved private HTTPS URL ending in /mcp; TLS certificate must match DNS."
  validation {
    condition = var.mcp_resource_url == "" || can(regex("^https://[^/]+/mcp$", var.mcp_resource_url))
    error_message = "MCP URL must be a private HTTPS host ending /mcp"
  }
}
