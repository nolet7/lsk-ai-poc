# Dedicated operator-invoked one-shot migration task; no ECS service.
# Master credential is visible only to this task definition's execution role.
resource "aws_iam_role" "migrate_execution" {
  count = var.enabled ? 1 : 0
  name = "lsk-p28-prod-migrate-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy_attachment" "migrate_execution" {
  count = var.enabled ? 1 : 0
  role = aws_iam_role.migrate_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
resource "aws_iam_role_policy" "migrate_secret" {
  count = var.enabled ? 1 : 0
  name = "migration-master-and-app-secret"
  role = aws_iam_role.migrate_execution[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [
        aws_db_instance.main[0].master_user_secret[0].secret_arn,
        var.app_db_secret_arn
      ]
    }]
  })
}
resource "aws_ecs_task_definition" "migrate" {
  count = var.enabled ? 1 : 0
  family = "lsk-p28-prod-migrate"
  network_mode = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu = "512"
  memory = "1024"
  execution_role_arn = aws_iam_role.migrate_execution[0].arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture = "X86_64"
  }
  container_definitions = jsonencode([{
    name = "migrate"
    image = var.ecr_image_uri
    essential = true
    readonlyRootFilesystem = true
    user = "10001"
    command = ["python", "-m", "phase28.migrate_postgres"]
    environment = [
      { name = "AWS_REGION", value = var.aws_region },
      { name = "LSK_DB_HOST", value = aws_db_instance.main[0].address },
      { name = "LSK_DB_PORT", value = "5432" },
      { name = "LSK_DB_NAME", value = var.db_name }
    ]
    secrets = [
      { name = "LSK_DB_USERNAME", valueFrom = "${aws_db_instance.main[0].master_user_secret[0].secret_arn}:username::" },
      { name = "LSK_DB_PASSWORD", valueFrom = "${aws_db_instance.main[0].master_user_secret[0].secret_arn}:password::" },
      { name = "LSK_APP_DB_USERNAME", valueFrom = "${var.app_db_secret_arn}:username::" },
      { name = "LSK_APP_DB_PASSWORD", valueFrom = "${var.app_db_secret_arn}:password::" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group" = aws_cloudwatch_log_group.app[0].name
        "awslogs-region" = var.aws_region
        "awslogs-stream-prefix" = "migrate"
      }
    }
  }])
  depends_on = [aws_iam_role_policy.migrate_secret]
}
