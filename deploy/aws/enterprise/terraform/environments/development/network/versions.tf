terraform {
  required_version = ">= 1.11.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0, < 7.0"
    }
  }
}
provider "aws" {
  region  = var.aws_region
  # In GitHub Actions, base credentials come from the management-account
  # state role; assume only an approved member-account workload role.
  profile = var.ci_mode ? null : var.aws_profile
  dynamic "assume_role" {
    for_each = var.ci_mode ? [var.ci_deployment_role_arn] : []
    content {
      role_arn     = assume_role.value
      session_name = "lsk-gha-network"
    }
  }
  default_tags {
    tags = {
      Project     = "lsk-ai-poc"
      Environment = "development"
      ManagedBy   = "terraform"
      Owner       = var.owner_tag
    }
  }
}
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}
