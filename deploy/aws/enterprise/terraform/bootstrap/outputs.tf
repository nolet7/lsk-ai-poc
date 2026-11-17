output "state_bucket_name" {
  description = "Remote state bucket (use in backend configuration in later tasks)."
  value       = aws_s3_bucket.state.id
}
output "state_bucket_arn" {
  value = aws_s3_bucket.state.arn
}
output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}
output "region" {
  value = var.aws_region
}
