data "aws_vpc" "selected" { id = var.vpc_id }
data "aws_subnet" "private" {
  for_each = toset(var.private_subnet_ids)
  id = each.value
}
data "aws_caller_identity" "current" {}

locals {
  name = "lsk-p28-prod"
  required_services = toset(["ecr.api", "ecr.dkr", "logs", "secretsmanager", "bedrock-runtime"])
  azs = distinct([for subnet in data.aws_subnet.private : subnet.availability_zone])
}

resource "aws_security_group" "alb" {
  count = var.enabled ? 1 : 0
  name_prefix = "${local.name}-alb-"
  vpc_id = var.vpc_id
  description = "Internal ALB accepts only explicitly approved client CIDRs"
}
resource "aws_vpc_security_group_ingress_rule" "alb_clients" {
  for_each = var.enabled ? toset(var.trusted_client_cidrs) : toset([])
  security_group_id = aws_security_group.alb[0].id
  cidr_ipv4 = each.value
  ip_protocol = "tcp"
  from_port = 443
  to_port = 443
}
resource "aws_security_group" "task" {
  count = var.enabled ? 1 : 0
  name_prefix = "${local.name}-task-"
  vpc_id = var.vpc_id
  description = "Private ECS tasks"
}
resource "aws_vpc_security_group_ingress_rule" "task_from_alb" {
  count = var.enabled ? 1 : 0
  security_group_id = aws_security_group.task[0].id
  referenced_security_group_id = aws_security_group.alb[0].id
  ip_protocol = "tcp"
  from_port = 8081
  to_port = 8081
}
resource "aws_vpc_security_group_egress_rule" "alb_to_task" {
  count = var.enabled ? 1 : 0
  security_group_id = aws_security_group.alb[0].id
  referenced_security_group_id = aws_security_group.task[0].id
  ip_protocol = "tcp"
  from_port = 8081
  to_port = 8081
}
resource "aws_security_group" "db" {
  count = var.enabled ? 1 : 0
  name_prefix = "${local.name}-db-"
  vpc_id = var.vpc_id
}
resource "aws_vpc_security_group_ingress_rule" "db_from_task" {
  count = var.enabled ? 1 : 0
  security_group_id = aws_security_group.db[0].id
  referenced_security_group_id = aws_security_group.task[0].id
  ip_protocol = "tcp"
  from_port = 5432
  to_port = 5432
}
resource "aws_vpc_security_group_egress_rule" "task_to_db" {
  count = var.enabled ? 1 : 0
  security_group_id = aws_security_group.task[0].id
  referenced_security_group_id = aws_security_group.db[0].id
  ip_protocol = "tcp"
  from_port = 5432
  to_port = 5432
}
resource "aws_security_group" "endpoint" {
  count = var.enabled ? 1 : 0
  name_prefix = "${local.name}-vpce-"
  vpc_id = var.vpc_id
}
resource "aws_vpc_security_group_ingress_rule" "endpoint_from_task" {
  count = var.enabled ? 1 : 0
  security_group_id = aws_security_group.endpoint[0].id
  referenced_security_group_id = aws_security_group.task[0].id
  ip_protocol = "tcp"
  from_port = 443
  to_port = 443
}
resource "aws_vpc_security_group_egress_rule" "task_to_endpoint" {
  count = var.enabled ? 1 : 0
  security_group_id = aws_security_group.task[0].id
  referenced_security_group_id = aws_security_group.endpoint[0].id
  ip_protocol = "tcp"
  from_port = 443
  to_port = 443
}
resource "aws_vpc_endpoint" "interface" {
  for_each = var.enabled ? local.required_services : toset([])
  vpc_id = var.vpc_id
  service_name = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type = "Interface"
  private_dns_enabled = true
  subnet_ids = var.private_subnet_ids
  security_group_ids = [aws_security_group.endpoint[0].id]
  tags = { Name = "${local.name}-${each.value}" }
}
# S3 gateway is needed for private ECR image layer downloads. Associate with
# the existing private subnet route tables via explicit, operator-reviewed IDs.
resource "aws_vpc_endpoint" "s3" {
  count = var.enabled ? 1 : 0
  vpc_id = var.vpc_id
  service_name = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids = var.private_route_table_ids
}
resource "aws_vpc_security_group_egress_rule" "task_to_s3" {
  count = var.enabled ? 1 : 0
  security_group_id = aws_security_group.task[0].id
  prefix_list_id = data.aws_prefix_list.s3.id
  ip_protocol = "tcp"
  from_port = 443
  to_port = 443
}
data "aws_prefix_list" "s3" { name = "com.amazonaws.${var.aws_region}.s3" }

resource "aws_db_subnet_group" "main" {
  count = var.enabled ? 1 : 0
  name = "${local.name}-db"
  subnet_ids = var.private_subnet_ids
}
resource "aws_db_instance" "main" {
  count = var.enabled ? 1 : 0
  identifier = "${local.name}-postgres"
  engine = "postgres"
  instance_class = var.db_instance_class
  allocated_storage = 20
  max_allocated_storage = 100
  storage_encrypted = true
  multi_az = true
  publicly_accessible = false
  db_name = var.db_name
  username = var.db_username
  manage_master_user_password = true
  db_subnet_group_name = aws_db_subnet_group.main[0].name
  vpc_security_group_ids = [aws_security_group.db[0].id]
  backup_retention_period = 7
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "${local.name}-final-snapshot"
  auto_minor_version_upgrade = true
  lifecycle {
    precondition {
      condition = length(local.azs) >= 2 && var.approved_release
      error_message = "Production must use >=2 AZs and explicitly approved_release=true."
    }
  }
}

resource "aws_cloudwatch_log_group" "app" {
  count = var.enabled ? 1 : 0
  name = "/ecs/${local.name}"
  retention_in_days = 30
}
resource "aws_iam_role" "execution" {
  count = var.enabled ? 1 : 0
  name = "${local.name}-execution"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "execution" {
  count = var.enabled ? 1 : 0
  role = aws_iam_role.execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
resource "aws_iam_role_policy" "execution_secret" {
  count = var.enabled ? 1 : 0
  name = "restricted-app-db-secret"
  role = aws_iam_role.execution[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = ["secretsmanager:GetSecretValue"],
    Resource = [var.app_db_secret_arn] }] })
}
resource "aws_iam_role" "task" {
  count = var.enabled ? 1 : 0
  name = "${local.name}-task"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy" "task" {
  count = var.enabled ? 1 : 0
  name = "bedrock-and-public-jwks"
  role = aws_iam_role.task[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = [var.bedrock_model_arn] },
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = [var.jwks_secret_arn] }
  ] })
}
resource "aws_ecs_cluster" "main" {
  count = var.enabled ? 1 : 0
  name = local.name
}
resource "aws_lb" "internal" {
  count = var.enabled ? 1 : 0
  name = local.name
  internal = true
  load_balancer_type = "application"
  subnets = var.private_subnet_ids
  security_groups = [aws_security_group.alb[0].id]
  enable_deletion_protection = true
}
resource "aws_lb_target_group" "app" {
  count = var.enabled ? 1 : 0
  name = "${local.name}-tg"
  port = 8081
  protocol = "HTTP"
  target_type = "ip"
  vpc_id = var.vpc_id
  health_check {
    path = "/health/ready"
    interval = 30
    healthy_threshold = 2
    unhealthy_threshold = 3
    matcher = "200"
  }
}
resource "aws_lb_listener" "https" {
  count = var.enabled ? 1 : 0
  load_balancer_arn = aws_lb.internal[0].arn
  port = 443
  protocol = "HTTPS"
  certificate_arn = var.alb_certificate_arn
  ssl_policy = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  default_action { 
    type = "forward"
    target_group_arn = aws_lb_target_group.app[0].arn
  }
}
resource "aws_ecs_task_definition" "app" {
  count = var.enabled ? 1 : 0
  family = local.name
  network_mode = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu = "512"
  memory = "1024"
  execution_role_arn = aws_iam_role.execution[0].arn
  task_role_arn = aws_iam_role.task[0].arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture = "X86_64"
  }
  container_definitions = jsonencode([{
    name = "api", image = var.ecr_image_uri, essential = true, readonlyRootFilesystem = true,
    user = "10001", portMappings = [{ containerPort = 8081, protocol = "tcp" }],
    environment = [
      { name = "AWS_REGION", value = var.aws_region },
      { name = "LSK_DB_HOST", value = aws_db_instance.main[0].address },
      { name = "LSK_DB_NAME", value = var.db_name },
      { name = "LSK_DB_PORT", value = "5432" },
      { name = "LSK_JWKS_SECRET_ARN", value = var.jwks_secret_arn },
      { name = "LSK_OIDC_ISSUER", value = var.oidc_issuer },
      { name = "LSK_OIDC_AUDIENCE", value = var.oidc_audience },
      { name = "LSK_RBAC_JSON", value = var.rbac_json },
      { name = "LSK_BEDROCK_MODEL_ID", value = var.bedrock_model_id },
      { name = "LSK_COMMERCIAL_WORKFLOW", value = tostring(var.enable_commercial_workflow) },
      { name = "LSK_MCP_URL", value = var.mcp_resource_url },
      { name = "AI_LIVE_INFERENCE", value = tostring(var.live_inference_enabled) },
      { name = "AI_LIVE_INFERENCE_ACK", value = tostring(var.live_inference_enabled) },
      { name = "LSK_MAX_DAILY_MODEL_CALLS", value = tostring(var.max_daily_model_calls) }
    ],
    secrets = [
      { name = "LSK_DB_USERNAME", valueFrom = "${var.app_db_secret_arn}:username::" },
      { name = "LSK_DB_PASSWORD", valueFrom = "${var.app_db_secret_arn}:password::" }
    ],
    logConfiguration = { logDriver = "awslogs", options = {
      "awslogs-group" = aws_cloudwatch_log_group.app[0].name,
      "awslogs-region" = var.aws_region,
      "awslogs-stream-prefix" = "api"
    } }
  }])
}
resource "aws_ecs_service" "app" {
  count = var.enabled ? 1 : 0
  name = local.name
  cluster = aws_ecs_cluster.main[0].id
  task_definition = aws_ecs_task_definition.app[0].arn
  desired_count = var.bootstrap_mode ? 0 : var.desired_tasks
  launch_type = "FARGATE"
  enable_execute_command = false
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent = 200
  network_configuration {
    subnets = var.private_subnet_ids
    assign_public_ip = false
    security_groups = [aws_security_group.task[0].id]
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.app[0].arn
    container_name = "api"
    container_port = 8081
  }
  deployment_circuit_breaker {
    enable = true
    rollback = true
  }
  depends_on = [aws_lb_listener.https, aws_vpc_endpoint.interface, aws_vpc_endpoint.s3,
                aws_iam_role_policy.execution_secret, aws_iam_role_policy.task]
  lifecycle {
    precondition {
      condition = var.approved_release && length(local.azs) >= 2 && can(regex("^arn:aws:sns:", var.alarm_topic_arn))
      error_message = "Explicit release approval and 2 AZs required."
    }
  }
}
resource "aws_appautoscaling_target" "tasks" {
  count = var.enabled ? 1 : 0
  max_capacity = max(4, var.desired_tasks * 2)
  min_capacity = var.bootstrap_mode ? 0 : 2
  resource_id = "service/${aws_ecs_cluster.main[0].name}/${aws_ecs_service.app[0].name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace = "ecs"
}
resource "aws_appautoscaling_policy" "cpu" {
  count = var.enabled ? 1 : 0
  name = "${local.name}-cpu-target"
  policy_type = "TargetTrackingScaling"
  resource_id = aws_appautoscaling_target.tasks[0].resource_id
  scalable_dimension = aws_appautoscaling_target.tasks[0].scalable_dimension
  service_namespace = aws_appautoscaling_target.tasks[0].service_namespace
  target_tracking_scaling_policy_configuration {
    target_value = 60
    predefined_metric_specification { predefined_metric_type = "ECSServiceAverageCPUUtilization" }
  }
}
