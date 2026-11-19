data "aws_vpc" "selected" { id = var.vpc_id }
data "aws_subnet" "selected" { id = var.private_subnet_id }
data "aws_caller_identity" "current" {}
locals {
  name = "lsk-p28-pilot"
  services = toset(["ssm", "ssmmessages", "bedrock-runtime"])
}
resource "aws_security_group" "app" {
  count = var.enabled ? 1 : 0
  name_prefix = "${local.name}-instance-"
  description = "Private EC2: no inbound ports"
  vpc_id = var.vpc_id
}
resource "aws_security_group" "endpoints" {
  count = var.enabled ? 1 : 0
  name_prefix = "${local.name}-vpce-"
  vpc_id = var.vpc_id
}
resource "aws_vpc_security_group_ingress_rule" "endpoints_from_instance" {
  count = var.enabled ? 1 : 0
  security_group_id = aws_security_group.endpoints[0].id
  referenced_security_group_id = aws_security_group.app[0].id
  ip_protocol = "tcp"
  from_port = 443
  to_port = 443
}
resource "aws_vpc_security_group_egress_rule" "instance_to_endpoints" {
  count = var.enabled ? 1 : 0
  security_group_id = aws_security_group.app[0].id
  referenced_security_group_id = aws_security_group.endpoints[0].id
  ip_protocol = "tcp"
  from_port = 443
  to_port = 443
}
resource "aws_vpc_endpoint" "private_services" {
  for_each = var.enabled ? local.services : toset([])
  vpc_id = var.vpc_id
  service_name = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type = "Interface"
  private_dns_enabled = true
  subnet_ids = [var.private_subnet_id]
  security_group_ids = [aws_security_group.endpoints[0].id]
  tags = { Name = "${local.name}-${each.value}" }
}
resource "aws_vpc_endpoint" "s3" {
  count = var.enabled && var.enable_s3_gateway ? 1 : 0
  vpc_id = var.vpc_id
  service_name = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids = var.private_route_table_ids
}
resource "aws_vpc_security_group_egress_rule" "instance_s3" {
  count = var.enabled && var.enable_s3_gateway ? 1 : 0
  security_group_id = aws_security_group.app[0].id
  prefix_list_id = data.aws_prefix_list.s3.id
  ip_protocol = "tcp"
  from_port = 443
  to_port = 443
}
data "aws_prefix_list" "s3" { name = "com.amazonaws.${var.aws_region}.s3" }
resource "aws_instance" "pilot" {
  count = var.enabled ? 1 : 0
  ami = var.ami_id
  instance_type = var.instance_type
  subnet_id = var.private_subnet_id
  associate_public_ip_address = false
  vpc_security_group_ids = [aws_security_group.app[0].id]
  iam_instance_profile = var.existing_instance_profile_name
  root_block_device {
    encrypted = true
    volume_type = "gp3"
    volume_size = 24
  }
  metadata_options {
    http_endpoint = "enabled"
    http_tokens = "required"
    http_put_response_hop_limit = 1
  }
  monitoring = true
  disable_api_termination = true
  tags = { Name = local.name }
  depends_on = [aws_vpc_endpoint.private_services, aws_vpc_endpoint.s3]
  lifecycle {
    precondition {
      condition = var.approved_change && data.aws_subnet.selected.vpc_id == var.vpc_id && !data.aws_subnet.selected.map_public_ip_on_launch
      error_message = "Explicit approval and verified private subnet in specified VPC required."
    }
  }
}
