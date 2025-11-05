# Adelaide Weather Forecast - Ephemeral Environment Variables

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "branch_name" {
  description = "Git branch name for the ephemeral environment"
  type        = string
}

variable "api_image" {
  description = "API Docker image URI"
  type        = string
}

variable "frontend_image" {
  description = "Frontend Docker image URI"
  type        = string
}

variable "domain_name" {
  description = "Base domain name for preview environments"
  type        = string
  default     = "preview.weather-forecast.dev"
}

variable "certificate_arn" {
  description = "ARN of wildcard SSL certificate for preview environments"
  type        = string
  default     = ""
}

variable "repository_url" {
  description = "GitHub repository URL"
  type        = string
  default     = "https://github.com/your-org/weather-forecast"
}