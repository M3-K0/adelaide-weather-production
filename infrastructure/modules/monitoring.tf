# Adelaide Weather Forecast Infrastructure - Monitoring & Alerting

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  count = var.enable_monitoring ? 1 : 0

  dashboard_name = "${local.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.api.name, "ClusterName", aws_ecs_cluster.main.name],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", aws_ecs_service.api.name, "ClusterName", aws_ecs_cluster.main.name],
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.frontend.name, "ClusterName", aws_ecs_cluster.main.name],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", aws_ecs_service.frontend.name, "ClusterName", aws_ecs_cluster.main.name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.region
          title   = "ECS Service Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.main.arn_suffix],
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", aws_lb.main.arn_suffix],
            ["AWS/ApplicationELB", "HTTPCode_Target_2XX_Count", "LoadBalancer", aws_lb.main.arn_suffix],
            ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", aws_lb.main.arn_suffix],
            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", aws_lb.main.arn_suffix]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.region
          title   = "Load Balancer Metrics"
          period  = 300
        }
      }
    ]
  })
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  count = var.enable_monitoring ? 1 : 0

  name = "${local.name_prefix}-alerts"

  tags = local.common_tags
}

# CloudWatch Alarms

# High CPU Utilization - API
resource "aws_cloudwatch_metric_alarm" "api_cpu_high" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-api-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors API CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    ServiceName = aws_ecs_service.api.name
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = local.common_tags
}

# High Memory Utilization - API
resource "aws_cloudwatch_metric_alarm" "api_memory_high" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-api-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors API memory utilization"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    ServiceName = aws_ecs_service.api.name
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = local.common_tags
}

# High Response Time
resource "aws_cloudwatch_metric_alarm" "response_time_high" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-response-time-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "5"
  alarm_description   = "This metric monitors ALB response time"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = local.common_tags
}

# High Error Rate (5XX)
resource "aws_cloudwatch_metric_alarm" "error_rate_high" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-error-rate-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors 5XX error rate"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = local.common_tags
}

# Target Health Check
resource "aws_cloudwatch_metric_alarm" "unhealthy_targets" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-unhealthy-targets"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "1"
  alarm_description   = "This metric monitors healthy target count"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    TargetGroup  = aws_lb_target_group.api.arn_suffix
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = local.common_tags
}

# Custom CloudWatch Metrics (Application-level)
resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  count = var.enable_monitoring ? 1 : 0

  name           = "${local.name_prefix}-api-errors"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "[timestamp, request_id, level=\"ERROR\", ...]"

  metric_transformation {
    name      = "APIErrors"
    namespace = "WeatherForecast/API"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "api_errors_high" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-api-errors-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "APIErrors"
  namespace           = "WeatherForecast/API"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "High number of API errors detected in logs"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]
  treat_missing_data  = "notBreaching"

  tags = local.common_tags
}

# Deployment monitoring (for blue-green deployments)
resource "aws_cloudwatch_metric_alarm" "deployment_failure" {
  count = var.enable_monitoring && var.deployment_strategy == "blue_green" ? 1 : 0

  alarm_name          = "${local.name_prefix}-deployment-failure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "DeploymentFailures"
  namespace           = "WeatherForecast/Deployment"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Deployment failure detected"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]
  treat_missing_data  = "notBreaching"

  tags = local.common_tags
}