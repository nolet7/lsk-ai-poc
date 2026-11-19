output "instance_id" { value = var.enabled ? aws_instance.pilot[0].id : null }
output "endpoint_ids" { value = { for service, endpoint in aws_vpc_endpoint.private_services : service => endpoint.id } }
output "pilot_security_group_id" { value = var.enabled ? aws_security_group.app[0].id : null }
