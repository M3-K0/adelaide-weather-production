# Adelaide Weather Forecast - Ephemeral Environment

terraform {
  required_version = ">= 1.6.0"
  
  backend "s3" {
    bucket = "weather-forecast-terraform-state"
    key    = "ephemeral/terraform.tfstate"
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
      Environment = "ephemeral"
      Branch      = var.branch_name
      Project     = "adelaide-weather-forecast"
      ManagedBy   = "terraform"
      Temporary   = "true"
    }
  }
}

locals {
  # Sanitize branch name for use in AWS resource names
  sanitized_branch = replace(replace(var.branch_name, "/", "-"), "_", "-")
  environment_name = "ephemeral-${local.sanitized_branch}"
}

module "weather_forecast" {
  source = "../modules"

  # Environment Configuration
  project_name = "weather-forecast"
  environment  = local.environment_name
  region       = var.region

  # Application Images
  api_image      = var.api_image
  frontend_image = var.frontend_image

  # Branch-specific configuration
  branch_name = var.branch_name

  # Minimal infrastructure for ephemeral environments
  instance_count              = 1
  api_cpu                    = 256
  api_memory                 = 512
  frontend_cpu               = 256
  frontend_memory            = 512
  enable_autoscaling         = false
  enable_monitoring          = false
  min_capacity              = 1
  max_capacity              = 2

  # Domain Configuration for preview environments
  domain_name     = var.domain_name
  certificate_arn = var.certificate_arn

  # Short-lived logging
  log_retention_days = 3

  # Repository
  repository_url = var.repository_url
}