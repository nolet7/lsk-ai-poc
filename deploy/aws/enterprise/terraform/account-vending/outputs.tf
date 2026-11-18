output "management_account_verified" {
  description = "True when the invoking principal belongs to the AWS Organizations management account."
  value       = data.aws_caller_identity.executor.account_id == data.aws_organizations_organization.current.master_account_id
}
output "development_account_id" {
  value       = try(aws_organizations_account.development[0].id, null)
  description = "Account ID only after approved creation and successful apply."
}
