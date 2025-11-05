# Adelaide Weather Forecast - Staging Environment

terraform {
  required_version = ">= 1.6.0"
  
  backend "s3" {
    bucket = "weather-forecast-terraform-state"
    key    = "staging/terraform.tfstate"
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
      Environment = "staging"
      Project     = "adelaide-weather-forecast"
      ManagedBy   = "terraform"
    }
  }
}

module "weather_forecast" {
  source = "../../modules"

  # Environment Configuration
  project_name = "weather-forecast"
  environment  = "staging"
  region       = var.region

  # Application Images
  api_image      = var.api_image
  frontend_image = var.frontend_image

  # Infrastructure Configuration (production-like)
  instance_count              = 2
  api_cpu                    = 512
  api_memory                 = 1024
  frontend_cpu               = 256
  frontend_memory            = 512
  enable_autoscaling         = true
  enable_monitoring          = true
  min_capacity              = 2
  max_capacity              = 6
  target_cpu_utilization    = 70

  # Domain Configuration
  domain_name     = var.domain_name
  certificate_arn = var.certificate_arn

  # Logging
  log_retention_days = 14

  # Repository
  repository_url = var.repository_url
}