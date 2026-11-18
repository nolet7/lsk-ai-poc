# Must run with authorized AWS Organizations MANAGEMENT account credentials.
# This Terraform root is separate from workload infrastructure and state.
data "aws_caller_identity" "executor" {}
data "aws_organizations_organization" "current" {}

resource "aws_organizations_account" "development" {
  count                      = var.create_account ? 1 : 0
  name                       = var.account_name
  email                      = var.account_email
  role_name                  = "OrganizationAccountAccessRole"
  parent_id                  = var.parent_ou_id
  close_on_deletion          = false
  iam_user_access_to_billing = "DENY"

  tags = {
    Application = "lsk-enterprise-ai"
    Environment = "development"
    CostCenter  = "ai-platform-lab"
  }

  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = data.aws_caller_identity.executor.account_id == data.aws_organizations_organization.current.master_account_id
      error_message = "Account vending must be executed from the Organizations management account, not the workload member account."
    }
    precondition {
      condition     = length(trimspace(var.account_email)) > 5 && can(regex("^[^@ ]+@[^@ ]+\\.[^@ ]+$", var.account_email))
      error_message = "Supply a valid dedicated contact email via TF_VAR_account_email before enabling create_account."
    }
  }
}
