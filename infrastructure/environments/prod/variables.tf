# Adelaide Weather Forecast - Production Environment Variables

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "api_image" {
  description = "API Docker image URI"
  type        = string
}

variable "frontend_image" {
  description = "Frontend Docker image URI"
  type        = string
}

variable "deployment_strategy" {
  description = "Deployment strategy (rolling, blue_green, canary)"
  type        = string
  default     = "blue_green"
}

variable "active_environment" {
  description = "Active environment for blue-green deployments (blue, green)"
  type        = string
  default     = "blue"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "weather-forecast.dev"
}

variable "certificate_arn" {
  description = "ARN of SSL certificate"
  type        = string
  default     = ""
}

variable "repository_url" {
  description = "GitHub repository URL"
  type        = string
  default     = "https://github.com/your-org/weather-forecast"
}