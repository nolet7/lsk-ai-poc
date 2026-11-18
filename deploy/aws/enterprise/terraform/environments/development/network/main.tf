# POC network only; NO EC2, public IPv4 allocation, NAT, EKS, ALB,
# VPC interface endpoints, Aurora or internet egress by default.
locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
  subnets = {
    public_a  = { tier = "public", az = 0, cidr = cidrsubnet(var.vpc_cidr, 8, 0) }
    public_b  = { tier = "public", az = 1, cidr = cidrsubnet(var.vpc_cidr, 8, 1) }
    private_a = { tier = "private", az = 0, cidr = cidrsubnet(var.vpc_cidr, 8, 10) }
    private_b = { tier = "private", az = 1, cidr = cidrsubnet(var.vpc_cidr, 8, 11) }
    data_a    = { tier = "data", az = 0, cidr = cidrsubnet(var.vpc_cidr, 8, 20) }
    data_b    = { tier = "data", az = 1, cidr = cidrsubnet(var.vpc_cidr, 8, 21) }
  }
}
resource "aws_vpc" "lsk" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "lsk-ai-dev-vpc" }
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == var.expected_account_id
      error_message = "STOP: Current AWS provider account is not the approved development account."
    }
  }
}
resource "aws_subnet" "tier" {
  for_each                = local.subnets
  vpc_id                  = aws_vpc.lsk.id
  cidr_block              = each.value.cidr
  availability_zone       = local.azs[each.value.az]
  map_public_ip_on_launch = false
  tags = {
    Name = "lsk-ai-dev-${each.key}"
    Tier = each.value.tier
  }
}
resource "aws_route_table" "tier" {
  for_each = toset(["public", "private", "data"])
  vpc_id   = aws_vpc.lsk.id
  tags     = { Name = "lsk-ai-dev-${each.key}-rt" }
}
resource "aws_route_table_association" "tier" {
  for_each       = local.subnets
  subnet_id      = aws_subnet.tier[each.key].id
  route_table_id = aws_route_table.tier[each.value.tier].id
}
resource "aws_internet_gateway" "public" {
  count  = var.enable_internet_gateway ? 1 : 0
  vpc_id = aws_vpc.lsk.id
  tags   = { Name = "lsk-ai-dev-igw" }
}
resource "aws_route" "public_internet" {
  count                  = var.enable_internet_gateway ? 1 : 0
  route_table_id         = aws_route_table.tier["public"].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.public[0].id
}
