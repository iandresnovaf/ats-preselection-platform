# Staging Environment Configuration
# terraform apply -var-file=environments/staging.tfvars

environment = "staging"
aws_region  = "us-east-1"

# VPC Configuration
vpc_cidr         = "10.1.0.0/16"
private_subnets  = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
public_subnets   = ["10.1.101.0/24", "10.1.102.0/24", "10.1.103.0/24"]
database_subnets = ["10.1.201.0/24", "10.1.202.0/24", "10.1.203.0/24"]

# RDS Configuration (small but production-like)
rds_instance_class        = "db.t3.small"
rds_allocated_storage     = 50
rds_max_allocated_storage = 100

# Redis Configuration
redis_node_type = "cache.t3.small"

# ECS Configuration
ecs_desired_count = 2
ecs_min_count     = 1
ecs_max_count     = 5
ecs_cpu           = 512
ecs_memory        = 1024
