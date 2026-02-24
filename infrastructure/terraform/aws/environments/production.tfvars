# Production Environment Configuration
# terraform apply -var-file=environments/production.tfvars

environment = "production"
aws_region  = "us-east-1"

# VPC Configuration
vpc_cidr         = "10.2.0.0/16"
private_subnets  = ["10.2.1.0/24", "10.2.2.0/24", "10.2.3.0/24"]
public_subnets   = ["10.2.101.0/24", "10.2.102.0/24", "10.2.103.0/24"]
database_subnets = ["10.2.201.0/24", "10.2.202.0/24", "10.2.203.0/24"]

# RDS Configuration (production grade)
rds_instance_class        = "db.r6g.large"
rds_allocated_storage     = 100
rds_max_allocated_storage = 500

# Redis Configuration
redis_node_type = "cache.r6g.large"

# ECS Configuration
ecs_desired_count = 3
ecs_min_count     = 2
ecs_max_count     = 20
ecs_cpu           = 1024
ecs_memory        = 2048
