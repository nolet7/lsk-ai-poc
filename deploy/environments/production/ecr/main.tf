resource "aws_ecr_repository" "api" {
  count = var.enabled ? 1 : 0
  name = var.repository_name
  image_tag_mutability = "IMMUTABLE"
  force_delete = false
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "AES256"
  }
  tags = {
    Project = "lsk-phase28-ai"
    Environment = "production"
  }
}
