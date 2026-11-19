output "diagnostic_instance_id" {
  value = try(aws_instance.diagnostic[0].id, null)
}

output "diagnostic_private_ip" {
  value = try(aws_instance.diagnostic[0].private_ip, null)
}

output "public_access_enabled" {
  value = false
}
