# Adelaide Weather Forecast - Development Environment Outputs

output "application_url" {
  description = "URL of the development application"
  value       = module.weather_forecast.application_url
}

output "api_url" {
  description = "URL of the development API"
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