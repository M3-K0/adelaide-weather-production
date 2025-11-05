# Adelaide Weather Forecast - Ephemeral Environment Outputs

output "application_url" {
  description = "URL of the ephemeral application"
  value       = module.weather_forecast.application_url
}

output "api_url" {
  description = "URL of the ephemeral API"
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

output "branch_name" {
  description = "Git branch name"
  value       = var.branch_name
}

output "environment_name" {
  description = "Environment name"
  value       = local.environment_name
}