# Adelaide Weather Forecast - Production Environment Outputs

output "application_url" {
  description = "URL of the production application"
  value       = module.weather_forecast.application_url
}

output "api_url" {
  description = "URL of the production API"
  value       = module.weather_forecast.api_url
}

output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = module.weather_forecast.alb_dns_name
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.weather_forecast.ecs_cluster_name
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.weather_forecast.vpc_id
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = module.weather_forecast.sns_topic_arn
}