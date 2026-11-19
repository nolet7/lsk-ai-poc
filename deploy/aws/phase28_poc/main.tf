terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "lsk-ai-poc-phase28"
      Environment = "poc"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.model_id}"
}

# These resources are opt-in and billable. With enabled=false, count=0.
resource "aws_security_group" "bedrock_endpoint" {
  count       = var.enabled ? 1 : 0
  name_prefix = "lsk-p28-bedrock-vpce-"
  description = "Private Bedrock runtime endpoint ingress"
  vpc_id      = var.vpc_id

  tags = { Name = "lsk-p28-bedrock-endpoint" }
}

resource "aws_vpc_security_group_ingress_rule" "application_tls" {
  count                        = var.enabled ? 1 : 0
  security_group_id            = aws_security_group.bedrock_endpoint[0].id
  referenced_security_group_id = var.application_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
  description                  = "TLS from approved application security group"
}

resource "aws_vpc_endpoint" "bedrock_runtime" {
  count               = var.enabled ? 1 : 0
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [aws_security_group.bedrock_endpoint[0].id]
  private_dns_enabled = true

  # Restrict the endpoint itself; no default broad-access endpoint policy.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "OnlyApprovedRoleAndModel"
      Effect    = "Allow"
      Principal = { AWS = var.application_role_arn }
      Action    = ["bedrock:InvokeModel"]
      Resource  = [local.model_arn]
    }]
  })

  tags = { Name = "lsk-p28-bedrock-runtime" }
}

resource "aws_iam_policy" "bedrock_invoke" {
  count       = var.enabled ? 1 : 0
  name_prefix = "lsk-p28-model-invoke-"
  description = "Converse permission for one model via one endpoint"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "InvokeOneModelFromOneEndpoint"
      Effect   = "Allow"
      Action   = ["bedrock:InvokeModel"]
      Resource = [local.model_arn]
      Condition = {
        StringEquals = { "aws:SourceVpce" = aws_vpc_endpoint.bedrock_runtime[0].id }
      }
    }]
  })
}

# Attaches permission to an EXISTING application IAM role; no trust policy created.
resource "aws_iam_role_policy_attachment" "bedrock_invoke" {
  count      = var.enabled ? 1 : 0
  role       = var.application_role_name
  policy_arn = aws_iam_policy.bedrock_invoke[0].arn
}
