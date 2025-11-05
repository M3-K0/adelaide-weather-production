# Adelaide Weather Forecast Infrastructure - Auto Scaling

# Auto Scaling Target for API Service
resource "aws_appautoscaling_target" "api" {
  count = var.enable_autoscaling ? 1 : 0

  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = local.common_tags
}

# Auto Scaling Target for Frontend Service
resource "aws_appautoscaling_target" "frontend" {
  count = var.enable_autoscaling ? 1 : 0

  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.frontend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = local.common_tags
}

# CPU-based Auto Scaling Policy for API
resource "aws_appautoscaling_policy" "api_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${local.name_prefix}-api-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api[0].resource_id
  scalable_dimension = aws_appautoscaling_target.api[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.api[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = var.target_cpu_utilization

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_out_cooldown = 300
    scale_in_cooldown  = 300
  }
}

# Memory-based Auto Scaling Policy for API
resource "aws_appautoscaling_policy" "api_memory" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${local.name_prefix}-api-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api[0].resource_id
  scalable_dimension = aws_appautoscaling_target.api[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.api[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }

    scale_out_cooldown = 300
    scale_in_cooldown  = 300
  }
}

# Request Count-based Auto Scaling Policy for API
resource "aws_appautoscaling_policy" "api_requests" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${local.name_prefix}-api-requests-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api[0].resource_id
  scalable_dimension = aws_appautoscaling_target.api[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.api[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 1000.0

    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.api.arn_suffix}"
    }

    scale_out_cooldown = 300
    scale_in_cooldown  = 300
  }
}

# CPU-based Auto Scaling Policy for Frontend
resource "aws_appautoscaling_policy" "frontend_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${local.name_prefix}-frontend-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend[0].resource_id
  scalable_dimension = aws_appautoscaling_target.frontend[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = var.target_cpu_utilization

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_out_cooldown = 300
    scale_in_cooldown  = 300
  }
}

# Request Count-based Auto Scaling Policy for Frontend
resource "aws_appautoscaling_policy" "frontend_requests" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${local.name_prefix}-frontend-requests-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend[0].resource_id
  scalable_dimension = aws_appautoscaling_target.frontend[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 1500.0

    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.frontend.arn_suffix}"
    }

    scale_out_cooldown = 300
    scale_in_cooldown  = 300
  }
}