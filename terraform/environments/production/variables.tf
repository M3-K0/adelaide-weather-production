# Production Environment Variables
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "adelaide-weather"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "deployment_id" {
  description = "Unique deployment identifier"
  type        = string
  default     = ""
}

variable "risk_level" {
  description = "Risk level of the deployment (low, medium, high)"
  type        = string
  default     = "medium"
  validation {
    condition     = contains(["low", "medium", "high"], var.risk_level)
    error_message = "Risk level must be one of: low, medium, high."
  }
}

variable "api_image_tag" {
  description = "API container image tag"
  type        = string
  default     = "production-latest"
}

variable "frontend_image_tag" {
  description = "Frontend container image tag"
  type        = string
  default     = "production-latest"
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# Application Configuration
variable "api_replica_count" {
  description = "Number of API replicas"
  type        = number
  default     = 3
}

variable "frontend_replica_count" {
  description = "Number of frontend replicas"
  type        = number
  default     = 3
}

variable "enable_monitoring" {
  description = "Enable monitoring stack"
  type        = bool
  default     = true
}

variable "enable_logging" {
  description = "Enable centralized logging"
  type        = bool
  default     = true
}

# Security Configuration
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_waf" {
  description = "Enable WAF protection"
  type        = bool
  default     = true
}

variable "enable_shield" {
  description = "Enable AWS Shield Advanced"
  type        = bool
  default     = false
}

# Database Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r5.large"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "db_backup_retention_period" {
  description = "DB backup retention period in days"
  type        = number
  default     = 30
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = true
}

variable "db_enable_performance_insights" {
  description = "Enable Performance Insights"
  type        = bool
  default     = true
}

# Cache Configuration
variable "cache_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.r6g.large"
}

variable "cache_num_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 3
}

variable "cache_enable_auth" {
  description = "Enable Redis AUTH"
  type        = bool
  default     = true
}

# Auto Scaling Configuration
variable "enable_autoscaling" {
  description = "Enable horizontal pod autoscaling"
  type        = bool
  default     = true
}

variable "api_min_replicas" {
  description = "Minimum number of API replicas"
  type        = number
  default     = 3
}

variable "api_max_replicas" {
  description = "Maximum number of API replicas"
  type        = number
  default     = 10
}

variable "frontend_min_replicas" {
  description = "Minimum number of frontend replicas"
  type        = number
  default     = 3
}

variable "frontend_max_replicas" {
  description = "Maximum number of frontend replicas"
  type        = number
  default     = 8
}

# Backup Configuration
variable "enable_cross_region_backup" {
  description = "Enable cross-region backup"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}

# Compliance and Governance
variable "enable_config" {
  description = "Enable AWS Config for compliance monitoring"
  type        = bool
  default     = true
}

variable "enable_cloudtrail" {
  description = "Enable CloudTrail for audit logging"
  type        = bool
  default     = true
}

variable "enable_guard_duty" {
  description = "Enable GuardDuty for threat detection"
  type        = bool
  default     = true
}

variable "compliance_tags" {
  description = "Tags for compliance and governance"
  type        = map(string)
  default = {
    DataClassification = "internal"
    BusinessCriticality = "high"
    ComplianceScope = "sox"
  }
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Enable spot instances for cost optimization"
  type        = bool
  default     = true
}

variable "spot_instance_percentage" {
  description = "Percentage of spot instances to use"
  type        = number
  default     = 30
  validation {
    condition     = var.spot_instance_percentage >= 0 && var.spot_instance_percentage <= 100
    error_message = "Spot instance percentage must be between 0 and 100."
  }
}

# Blue-Green Deployment Configuration
variable "enable_blue_green" {
  description = "Enable blue-green deployment infrastructure"
  type        = bool
  default     = true
}

variable "blue_green_traffic_split" {
  description = "Traffic split percentage for blue-green deployment"
  type        = number
  default     = 0
  validation {
    condition     = var.blue_green_traffic_split >= 0 && var.blue_green_traffic_split <= 100
    error_message = "Traffic split percentage must be between 0 and 100."
  }
}

# Resource Tags
variable "additional_tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Certificate ARN for HTTPS
variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
  default     = ""
}

# Domain Configuration
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "adelaide-weather.example.com"
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID"
  type        = string
  default     = ""
}