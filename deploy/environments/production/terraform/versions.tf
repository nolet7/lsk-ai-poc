terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  # Add organization-approved encrypted S3 backend in backend.hcl, never commit state.
}
provider "aws" { region = var.aws_region
  default_tags { tags = {
    Project = "lsk-phase28-ai"
    Environment = "production"
    ManagedBy = "terraform"
  } }
}
