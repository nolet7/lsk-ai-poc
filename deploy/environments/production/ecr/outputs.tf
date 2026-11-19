output "repository_url" {
  value = var.enabled ? aws_ecr_repository.api[0].repository_url : null
}
output "repository_arn" {
  value = var.enabled ? aws_ecr_repository.api[0].arn : null
}
