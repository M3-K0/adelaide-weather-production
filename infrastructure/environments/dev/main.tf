# Adelaide Weather Forecast - Development Environment

terraform {
  required_version = ">= 1.6.0"
  
  backend "s3" {
    # Configure this with your actual S3 bucket
    bucket = "weather-forecast-terraform-state"
    key    = "dev/terraform.tfstate"
    region = "us-east-1"
    
    # Optional: Enable state locking with DynamoDB
    # dynamodb_table = "terraform-state-lock"
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
      Environment = "development"
      Project     = "adelaide-weather-forecast"
      ManagedBy   = "terraform"
    }
  }
}

module "weather_forecast" {
  source = "../../modules"

  # Environment Configuration
  project_name = "weather-forecast"
  environment  = "dev"
  region       = var.region

  # Application Images
  api_image      = var.api_image
  frontend_image = var.frontend_image

  # Infrastructure Configuration
  instance_count              = 1
  api_cpu                    = 256
  api_memory                 = 512
  frontend_cpu               = 256
  frontend_memory            = 512
  enable_autoscaling         = false
  enable_monitoring          = true
  min_capacity              = 1
  max_capacity              = 3
  target_cpu_utilization    = 70

  # Domain Configuration
  domain_name     = var.domain_name
  certificate_arn = var.certificate_arn

  # Logging
  log_retention_days = 7

  # Repository
  repository_url = var.repository_url
}