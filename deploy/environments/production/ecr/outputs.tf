output "repository_url" {
  value = var.enabled ? aws_ecr_repository.api[0].repository_url : null
}
output "repository_arn" {
  value = var.enabled ? aws_ecr_repository.api[0].arn : null
}
output "github_oidc_publisher_role_arn" {
  value = var.enabled ? aws_iam_role.publisher[0].arn : null
}
