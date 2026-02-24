# Development Environment Configuration
# terraform apply -var-file=environments/dev.tfvars

environment = "dev"
aws_region  = "us-east-1"

# VPC Configuration
vpc_cidr         = "10.0.0.0/16"
private_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
public_subnets   = ["10.0.101.0/24", "10.0.102.0/24"]
database_subnets = ["10.0.201.0/24", "10.0.202.0/24"]

# RDS Configuration (minimal for dev)
rds_instance_class        = "db.t3.micro"
rds_allocated_storage     = 20
rds_max_allocated_storage = 50

# Redis Configuration
redis_node_type = "cache.t3.micro"

# ECS Configuration
ecs_desired_count = 1
ecs_min_count     = 1
ecs_max_count     = 2
ecs_cpu           = 256
ecs_memory        = 512
