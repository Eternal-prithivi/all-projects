# Template: Backend Application
# Deploys: VPC + EC2 (t2.micro) + IAM role + Budget alert
# Estimated cost: $0.00/month (within AWS Free Tier, 750 hours/month)

aws_region = "ap-south-1"

# Feature flags
enable_vpc        = true
enable_ec2        = true
enable_s3         = false
enable_iam        = true
enable_cloudwatch = true
enable_dynamodb   = false

# VPC
vpc_cidr = "10.0.0.0/16"

# EC2
instance_type = "t2.micro"
ami_id        = ""  # Will be populated per-region (Amazon Linux 2)
instance_name = ""  # Will be populated: zenith-{username}-app

# IAM
role_name = ""  # Will be populated: zenith-{username}-role

# CloudWatch
alarm_email = ""  # Populated from user profile

# Budget
budget_limit = "1"
budget_email = ""  # Populated from user profile

# Tags
tags = {
  Owner   = ""
  Project = "zenith-backend-app"
  Env     = "free-tier"
  ManagedBy = "zenith-provision"
}
