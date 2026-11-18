output "account_verified" {
  value = data.aws_caller_identity.current.account_id == var.expected_account_id
}
output "vpc_id" {
  value = aws_vpc.lsk.id
}
output "availability_zones" {
  value = local.azs
}
output "subnet_ids" {
  value = { for name, subnet in aws_subnet.tier : name => subnet.id }
}
output "route_tables" {
  value = { for tier, route in aws_route_table.tier : tier => route.id }
}
output "internet_gateway_enabled" {
  value = var.enable_internet_gateway
}
