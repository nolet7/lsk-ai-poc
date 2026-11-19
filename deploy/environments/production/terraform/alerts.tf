# Infra-level alerting. This is NOT an end-to-end AI SLO or model quality monitor.
resource "aws_cloudwatch_metric_alarm" "ecs_cpu" {
  count = var.enabled ? 1 : 0
  alarm_name = "lsk-p28-prod-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods = 2
  period = 300
  threshold = 85
  metric_name = "CPUUtilization"
  namespace = "AWS/ECS"
  statistic = "Average"
  dimensions = {
    ClusterName = aws_ecs_cluster.main[0].name
    ServiceName = aws_ecs_service.app[0].name
  }
  alarm_actions = [var.alarm_topic_arn]
  treat_missing_data = "notBreaching"
}
resource "aws_cloudwatch_metric_alarm" "alb_target_5xx" {
  count = var.enabled ? 1 : 0
  alarm_name = "lsk-p28-prod-alb-target-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods = 2
  period = 300
  threshold = 5
  metric_name = "HTTPCode_Target_5XX_Count"
  namespace = "AWS/ApplicationELB"
  statistic = "Sum"
  dimensions = {
    LoadBalancer = aws_lb.internal[0].arn_suffix
    TargetGroup = aws_lb_target_group.app[0].arn_suffix
  }
  alarm_actions = [var.alarm_topic_arn]
  treat_missing_data = "notBreaching"
}
resource "aws_cloudwatch_metric_alarm" "rds_free_storage" {
  count = var.enabled ? 1 : 0
  alarm_name = "lsk-p28-prod-db-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods = 2
  period = 300
  threshold = 2147483648
  metric_name = "FreeStorageSpace"
  namespace = "AWS/RDS"
  statistic = "Average"
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main[0].identifier
  }
  alarm_actions = [var.alarm_topic_arn]
  treat_missing_data = "missing"
}
