# Adelaide Weather Forecast - Production Environment

terraform {
  required_version = ">= 1.6.0"
  
  backend "s3" {
    bucket = "weather-forecast-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
  
  default_tags {
    tags = {
      Environment = "production"
      Project     = "adelaide-weather-forecast"
      ManagedBy   = "terraform"
    }
  }
}

module "weather_forecast" {
  source = "../../modules"

  # Environment Configuration
  project_name = "weather-forecast"
  environment  = "prod"
  region       = var.region

  # Application Images
  api_image      = var.api_image
  frontend_image = var.frontend_image

  # Deployment Strategy
  deployment_strategy = var.deployment_strategy
  active_environment  = var.active_environment

  # Infrastructure Configuration (production-scale)
  instance_count              = 3
  api_cpu                    = 1024
  api_memory                 = 2048
  frontend_cpu               = 512
  frontend_memory            = 1024
  enable_autoscaling         = true
  enable_monitoring          = true
  min_capacity              = 3
  max_capacity              = 10
  target_cpu_utilization    = 60

  # Domain Configuration
  domain_name     = var.domain_name
  certificate_arn = var.certificate_arn

  # Database Configuration
  database_instance_class     = "db.t3.small"
  database_allocated_storage  = 100
  backup_retention_period    = 30

  # Logging
  log_retention_days = 30

  # Repository
  repository_url = var.repository_url
}