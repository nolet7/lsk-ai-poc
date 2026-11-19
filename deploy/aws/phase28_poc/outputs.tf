output "infrastructure_enabled" {
  value = var.enabled
}
output "bedrock_endpoint_id" {
  value = try(aws_vpc_endpoint.bedrock_runtime[0].id, null)
}
output "bedrock_endpoint_service" {
  value = var.enabled ? "com.amazonaws.${var.aws_region}.bedrock-runtime" : null
}
output "model_arn" {
  value = var.enabled ? local.model_arn : null
}
