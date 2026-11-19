output "internal_alb_dns_name" { value = var.enabled ? aws_lb.internal[0].dns_name : null }
output "ecs_cluster" { value = var.enabled ? aws_ecs_cluster.main[0].name : null }
output "ecs_service" { value = var.enabled ? aws_ecs_service.app[0].name : null }
output "database_endpoint" { value = var.enabled ? aws_db_instance.main[0].endpoint : null }
output "rds_secret_arn" { value = var.enabled ? aws_db_instance.main[0].master_user_secret[0].secret_arn : null
  sensitive = true
}
