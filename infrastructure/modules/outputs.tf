# Adelaide Weather Forecast Infrastructure - Outputs

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "alb_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.main.arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "api_service_name" {
  description = "Name of the API ECS service"
  value       = aws_ecs_service.api.name
}

output "frontend_service_name" {
  description = "Name of the frontend ECS service"
  value       = aws_ecs_service.frontend.name
}

output "api_target_group_arn" {
  description = "ARN of the API target group"
  value       = aws_lb_target_group.api.arn
}

output "frontend_target_group_arn" {
  description = "ARN of the frontend target group"
  value       = aws_lb_target_group.frontend.arn
}

output "cloudwatch_log_group_api" {
  description = "CloudWatch log group for API"
  value       = aws_cloudwatch_log_group.api.name
}

output "cloudwatch_log_group_frontend" {
  description = "CloudWatch log group for frontend"
  value       = aws_cloudwatch_log_group.frontend.name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = var.enable_monitoring ? aws_sns_topic.alerts[0].arn : null
}

output "application_url" {
  description = "URL of the application"
  value = var.environment == "prod" ? (
    var.certificate_arn == "" ? "https://${var.domain_name}" : "https://${aws_lb.main.dns_name}"
  ) : (
    var.certificate_arn == "" ? "https://${var.environment}.${var.domain_name}" : "https://${aws_lb.main.dns_name}"
  )
}

output "api_url" {
  description = "URL of the API"
  value = var.environment == "prod" ? (
    var.certificate_arn == "" ? "https://api.${var.domain_name}" : "https://${aws_lb.main.dns_name}"
  ) : (
    var.certificate_arn == "" ? "https://api-${var.environment}.${var.domain_name}" : "https://${aws_lb.main.dns_name}"
  )
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "region" {
  description = "AWS region"
  value       = var.region
}