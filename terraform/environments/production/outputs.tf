# Production Environment Outputs
output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = module.eks.cluster_oidc_issuer_url
}

output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = var.domain_name
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnets
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "database_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "cache_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "cache_port" {
  description = "ElastiCache Redis port"
  value       = aws_elasticache_replication_group.main.port
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for application data"
  value       = aws_s3_bucket.app_data.id
}

output "log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.app_logs.name
}

# Security Outputs
output "waf_web_acl_arn" {
  description = "WAF Web ACL ARN"
  value       = var.enable_waf ? aws_wafv2_web_acl.main[0].arn : null
}

output "db_password_secret_arn" {
  description = "ARN of the database password secret"
  value       = aws_secretsmanager_secret.db_password.arn
  sensitive   = true
}

output "redis_auth_secret_arn" {
  description = "ARN of the Redis auth token secret"
  value       = aws_secretsmanager_secret.redis_auth_token.arn
  sensitive   = true
}

# Environment Information
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "region" {
  description = "AWS region"
  value       = data.aws_region.current.name
}

output "account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

# Blue-Green Deployment Support
output "blue_environment" {
  description = "Blue environment identifier"
  value       = "blue"
}

output "green_environment" {
  description = "Green environment identifier"
  value       = "green"
}

output "active_environment" {
  description = "Currently active environment"
  value       = var.blue_green_traffic_split > 50 ? "green" : "blue"
}

output "deployment_id" {
  description = "Current deployment identifier"
  value       = var.deployment_id
}

output "risk_level" {
  description = "Deployment risk level"
  value       = var.risk_level
}

# High Availability Information
output "availability_zones" {
  description = "Availability zones in use"
  value       = slice(data.aws_availability_zones.available.names, 0, 3)
}

output "multi_az_enabled" {
  description = "Whether multi-AZ is enabled for critical services"
  value = {
    database = aws_db_instance.main.multi_az
    cache    = aws_elasticache_replication_group.main.multi_az_enabled
  }
}

# Kubernetes Configuration
output "kubeconfig_command" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${data.aws_region.current.name} --name ${module.eks.cluster_name}"
}

# Application URLs
output "api_url" {
  description = "API base URL"
  value       = "https://${var.domain_name}/api"
}

output "frontend_url" {
  description = "Frontend URL"
  value       = "https://${var.domain_name}"
}

output "monitoring_url" {
  description = "Monitoring dashboard URL"
  value       = "https://${var.domain_name}/grafana"
}

# Load Balancer Information
output "load_balancer_controller_role_arn" {
  description = "ARN of the AWS Load Balancer Controller IAM role"
  value       = aws_iam_role.aws_load_balancer_controller.arn
}

# Monitoring and Logging
output "cloudwatch_log_groups" {
  description = "CloudWatch log groups"
  value = {
    application = aws_cloudwatch_log_group.app_logs.name
    cluster     = aws_cloudwatch_log_group.cluster_logs.name
  }
}

# Networking
output "nat_gateway_ips" {
  description = "Elastic IPs of NAT Gateways"
  value       = module.vpc.nat_public_ips
}

# Cost Optimization Information
output "spot_instances_enabled" {
  description = "Whether spot instances are enabled"
  value       = var.enable_spot_instances
}

output "cost_allocation_tags" {
  description = "Tags used for cost allocation"
  value = {
    Project     = var.project_name
    Environment = var.environment
    CostCenter  = "engineering"
  }
}

# Compliance and Security
output "compliance_features" {
  description = "Enabled compliance and security features"
  value = {
    waf_enabled         = var.enable_waf
    config_enabled      = var.enable_config
    cloudtrail_enabled  = var.enable_cloudtrail
    guardduty_enabled   = var.enable_guard_duty
    encryption_at_rest  = true
    encryption_in_transit = true
  }
}

# Capacity and Scaling
output "autoscaling_configuration" {
  description = "Auto scaling configuration"
  value = {
    api_min_replicas      = var.api_min_replicas
    api_max_replicas      = var.api_max_replicas
    frontend_min_replicas = var.frontend_min_replicas
    frontend_max_replicas = var.frontend_max_replicas
  }
}

# Backup and Recovery
output "backup_configuration" {
  description = "Backup and recovery configuration"
  value = {
    db_backup_retention     = var.db_backup_retention_period
    cache_snapshot_retention = 7
    cross_region_backup     = var.enable_cross_region_backup
  }
}