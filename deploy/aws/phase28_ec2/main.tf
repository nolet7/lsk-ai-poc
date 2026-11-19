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
}

# Intentionally no public IP, SSH ingress, load balancer or auto-bootstrap.
# Apply is billable and requires a separately approved change.
resource "aws_security_group" "diagnostic" {
  count       = var.enabled ? 1 : 0
  name_prefix = "lsk-p28-diag-"
  description = "No inbound rules for Phase28 diagnostic-only instance"
  vpc_id      = var.vpc_id
  tags        = { Name = "lsk-p28-diagnostic" }
}

# Limited outbound TCP 443 still requires approved NAT/VPC endpoints and egress controls.
resource "aws_vpc_security_group_egress_rule" "https" {
  count             = var.enabled ? 1 : 0
  security_group_id = aws_security_group.diagnostic[0].id
  cidr_ipv4         = var.egress_cidr
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  description       = "Approved HTTPS egress; restrict CIDR in production"
}

resource "aws_instance" "diagnostic" {
  count                       = var.enabled ? 1 : 0
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.private_subnet_id
  associate_public_ip_address = false
  vpc_security_group_ids      = [aws_security_group.diagnostic[0].id]
  iam_instance_profile        = var.existing_instance_profile_name
  monitoring                  = true
  disable_api_termination     = true

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    encrypted   = true
    volume_type = "gp3"
    volume_size = 16
  }

  tags = {
    Name        = "lsk-phase28-diagnostic"
    Environment = "poc"
    ManagedBy   = "terraform"
  }

  lifecycle {
    precondition {
      condition = !var.enabled || (
        var.ami_id != "" && var.vpc_id != "" && var.private_subnet_id != "" && var.existing_instance_profile_name != ""
      )
      error_message = "Operator must provide an approved AMI, VPC, private subnet and existing instance profile"
    }
  }
}
