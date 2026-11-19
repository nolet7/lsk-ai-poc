# Existing GitHub OIDC provider must be supplied by account IAM administrator.
# Environment name in trust claim MUST be protected by reviewer/branch policies.
resource "aws_iam_role" "publisher" {
  count = var.enabled ? 1 : 0
  name = "lsk-p28-ecr-publisher"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = var.github_oidc_provider_arn }
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:nolet7/lsk-ai-poc:environment:production-image-publish"
        }
      }
    }]
  })
}
resource "aws_iam_role_policy" "publisher" {
  count = var.enabled ? 1 : 0
  name = "ecr-push-only"
  role = aws_iam_role.publisher[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "ecr:GetAuthorizationToken", Resource = "*" },
      { Effect = "Allow",
        Action = ["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
                  "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:DescribeImages"],
        Resource = aws_ecr_repository.api[0].arn
      }
    ]
  })
}
