# Private MCP service. Activated only after approved DNS, OIDC and DB migration.
# Shares approved immutable image and ALB; different ECS service and task role.
resource "aws_lb_target_group" "mcp" {
  count = var.enabled && var.enable_commercial_workflow ? 1 : 0
  name = "lsk-p28-prod-mcp"
  port = 8082
  protocol = "HTTP"
  target_type = "ip"
  vpc_id = var.vpc_id
  health_check {
    path = "/health/ready"
    matcher = "200"
    interval = 30
    healthy_threshold = 2
    unhealthy_threshold = 3
  }
}
resource "aws_vpc_security_group_ingress_rule" "mcp_from_alb" {
  count = var.enabled && var.enable_commercial_workflow ? 1 : 0
  security_group_id = aws_security_group.task[0].id
  referenced_security_group_id = aws_security_group.alb[0].id
  ip_protocol = "tcp"
  from_port = 8082
  to_port = 8082
}
resource "aws_vpc_security_group_egress_rule" "alb_to_mcp" {
  count = var.enabled && var.enable_commercial_workflow ? 1 : 0
  security_group_id = aws_security_group.alb[0].id
  referenced_security_group_id = aws_security_group.task[0].id
  ip_protocol = "tcp"
  from_port = 8082
  to_port = 8082
}
resource "aws_vpc_security_group_ingress_rule" "alb_from_api" {
  count = var.enabled && var.enable_commercial_workflow ? 1 : 0
  security_group_id = aws_security_group.alb[0].id
  referenced_security_group_id = aws_security_group.task[0].id
  ip_protocol = "tcp"
  from_port = 443
  to_port = 443
}
resource "aws_vpc_security_group_egress_rule" "api_to_alb" {
  count = var.enabled && var.enable_commercial_workflow ? 1 : 0
  security_group_id = aws_security_group.task[0].id
  referenced_security_group_id = aws_security_group.alb[0].id
  ip_protocol = "tcp"
  from_port = 443
  to_port = 443
}
resource "aws_lb_listener_rule" "mcp" {
  count = var.enabled && var.enable_commercial_workflow ? 1 : 0
  listener_arn = aws_lb_listener.https[0].arn
  priority = 20
  condition {
    path_pattern {
      values = ["/mcp", "/mcp/*", "/.well-known/oauth-protected-resource/*"]
    }
  }
  action {
    type = "forward"
    target_group_arn = aws_lb_target_group.mcp[0].arn
  }
}
resource "aws_iam_role" "mcp" {
  count = var.enabled && var.enable_commercial_workflow ? 1 : 0
  name = "lsk-p28-prod-mcp-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy" "mcp" {
  count = var.enabled && var.enable_commercial_workflow ? 1 : 0
  name = "read-public-jwks-only"
  role = aws_iam_role.mcp[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [var.jwks_secret_arn]
    }]
  })
}
resource "aws_ecs_task_definition" "mcp" {
  count = var.enabled && var.enable_commercial_workflow ? 1 : 0
  family = "lsk-p28-prod-mcp"
  network_mode = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu = "512"
  memory = "1024"
  execution_role_arn = aws_iam_role.execution[0].arn
  task_role_arn = aws_iam_role.mcp[0].arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture = "X86_64"
  }
  container_definitions = jsonencode([{
    name = "mcp", image = var.ecr_image_uri, essential = true,
    readonlyRootFilesystem = true, user = "10001",
    command = ["python", "-m", "phase28.fde_commercial.mcp_server"],
    portMappings = [{ containerPort = 8082, protocol = "tcp" }],
    environment = [
      { name = "AWS_REGION", value = var.aws_region },
      { name = "LSK_DB_HOST", value = aws_db_instance.main[0].address },
      { name = "LSK_DB_PORT", value = "5432" },
      { name = "LSK_DB_NAME", value = var.db_name },
      { name = "LSK_JWKS_SECRET_ARN", value = var.jwks_secret_arn },
      { name = "LSK_OIDC_ISSUER", value = var.oidc_issuer },
      { name = "LSK_OIDC_AUDIENCE", value = var.oidc_audience },
      { name = "LSK_MCP_PUBLIC_URL", value = var.mcp_resource_url },
      { name = "LSK_MCP_PORT", value = "8082" },
      { name = "LSK_RBAC_JSON", value = var.rbac_json },
      { name = "LSK_BEDROCK_MODEL_ID", value = var.bedrock_model_id }
    ],
    secrets = [
      { name = "LSK_DB_USERNAME", valueFrom = "${var.app_db_secret_arn}:username::" },
      { name = "LSK_DB_PASSWORD", valueFrom = "${var.app_db_secret_arn}:password::" }
    ],
    logConfiguration = {
      logDriver = "awslogs",
      options = {
        "awslogs-group" = aws_cloudwatch_log_group.app[0].name,
        "awslogs-region" = var.aws_region,
        "awslogs-stream-prefix" = "mcp"
      }
    }
  }])
  lifecycle {
    precondition {
      condition = can(regex("^https://[^/]+/mcp$", var.mcp_resource_url))
      error_message = "MCP requires valid private HTTPS resource URL."
    }
  }
}
resource "aws_ecs_service" "mcp" {
  count = var.enabled && var.enable_commercial_workflow ? 1 : 0
  name = "lsk-p28-prod-mcp"
  cluster = aws_ecs_cluster.main[0].id
  task_definition = aws_ecs_task_definition.mcp[0].arn
  desired_count = var.bootstrap_mode ? 0 : 2
  launch_type = "FARGATE"
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent = 200
  network_configuration {
    subnets = var.private_subnet_ids
    security_groups = [aws_security_group.task[0].id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.mcp[0].arn
    container_name = "mcp"
    container_port = 8082
  }
  deployment_circuit_breaker {
    enable = true
    rollback = true
  }
  depends_on = [aws_lb_listener_rule.mcp]
}
