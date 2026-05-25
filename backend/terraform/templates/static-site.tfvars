# Template: Static Site
# Deploys: S3 bucket (private, encrypted) + Budget alert
# Estimated cost: $0.00/month (within AWS Free Tier)

aws_region = "ap-south-1"

# Feature flags
enable_vpc        = false
enable_ec2        = false
enable_s3         = true
enable_iam        = false
enable_cloudwatch = false
enable_dynamodb   = false

# S3 configuration
bucket_name = ""  # Will be populated per-user: zenith-{username}-{timestamp}

# Budget
budget_limit = "1"
budget_email = ""  # Populated from user profile

# Tags
tags = {
  Owner   = ""
  Project = "zenith-static-site"
  Env     = "free-tier"
  ManagedBy = "zenith-provision"
}
