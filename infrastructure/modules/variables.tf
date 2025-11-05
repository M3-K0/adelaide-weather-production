# Adelaide Weather Forecast Infrastructure - Variables

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "weather-forecast"
}

variable "environment" {
  description = "Environment name (dev, staging, prod, ephemeral)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod", "ephemeral"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod, ephemeral."
  }
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "repository_url" {
  description = "GitHub repository URL"
  type        = string
  default     = "https://github.com/your-org/weather-forecast"
}

variable "api_image" {
  description = "API Docker image URI"
  type        = string
}

variable "frontend_image" {
  description = "Frontend Docker image URI"
  type        = string
}

variable "branch_name" {
  description = "Git branch name (used for ephemeral environments)"
  type        = string
  default     = ""
}

variable "deployment_strategy" {
  description = "Deployment strategy (rolling, blue_green, canary)"
  type        = string
  default     = "rolling"
  validation {
    condition     = contains(["rolling", "blue_green", "canary"], var.deployment_strategy)
    error_message = "Deployment strategy must be one of: rolling, blue_green, canary."
  }
}

variable "active_environment" {
  description = "Active environment for blue-green deployments (blue, green)"
  type        = string
  default     = "blue"
  validation {
    condition     = contains(["blue", "green"], var.active_environment)
    error_message = "Active environment must be one of: blue, green."
  }
}

variable "instance_count" {
  description = "Number of instances to run"
  type        = number
  default     = 2
}

variable "instance_type" {
  description = "ECS task instance type configuration"
  type        = string
  default     = "t3.medium"
}

variable "api_cpu" {
  description = "CPU units for API container (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Memory for API container in MB"
  type        = number
  default     = 1024
}

variable "frontend_cpu" {
  description = "CPU units for frontend container (1024 = 1 vCPU)"
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "Memory for frontend container in MB"
  type        = number
  default     = 512
}

variable "enable_monitoring" {
  description = "Enable monitoring and alerting"
  type        = bool
  default     = true
}

variable "enable_autoscaling" {
  description = "Enable auto scaling"
  type        = bool
  default     = true
}

variable "min_capacity" {
  description = "Minimum number of tasks"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of tasks"
  type        = number
  default     = 10
}

variable "target_cpu_utilization" {
  description = "Target CPU utilization for auto scaling"
  type        = number
  default     = 70
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

variable "database_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "database_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "backup_retention_period" {
  description = "Database backup retention period in days"
  type        = number
  default     = 7
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 14
}