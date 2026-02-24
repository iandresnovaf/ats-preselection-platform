# ==========================================
# Outputs - Terraform AWS Infrastructure
# ==========================================

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = module.vpc.public_subnets
}

output "database_subnet_ids" {
  description = "IDs of database subnets"
  value       = module.vpc.database_subnets
}

# RDS Outputs
output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.this.address
  sensitive   = false
}

output "rds_port" {
  description = "RDS PostgreSQL port"
  value       = aws_db_instance.this.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.this.db_name
}

output "rds_username" {
  description = "RDS master username"
  value       = aws_db_instance.this.username
}

output "rds_secret_arn" {
  description = "ARN of the secret containing RDS credentials"
  value       = aws_secretsmanager_secret.rds_password.arn
}

# Redis Outputs
output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.this.cache_nodes[0].address
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = aws_elasticache_cluster.this.port
}

# Security Group Outputs
output "rds_security_group_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.rds.id
}

output "redis_security_group_id" {
  description = "Security group ID for Redis"
  value       = aws_security_group.redis.id
}

output "alb_security_group_id" {
  description = "Security group ID for ALB"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "Security group ID for ECS"
  value       = aws_security_group.ecs.id
}

# S3 Outputs
output "uploads_bucket_name" {
  description = "Name of the S3 bucket for uploads"
  value       = aws_s3_bucket.uploads.id
}

output "uploads_bucket_arn" {
  description = "ARN of the S3 bucket for uploads"
  value       = aws_s3_bucket.uploads.arn
}

# Connection Strings (sensitive)
output "database_url" {
  description = "Database connection URL (sensitive)"
  value       = "postgresql://ats_admin:${random_password.rds_password.result}@${aws_db_instance.this.address}:5432/ats_platform"
  sensitive   = true
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "redis://${aws_elasticache_cluster.this.cache_nodes[0].address}:6379/0"
}
