# backend.tf — Remote State Configuration (Option A: S3 + DynamoDB)
# S3 bucket name: terraform-state-412628362844
# DynamoDB table: terraform-state-lock
# Region: ap-south-1 (Mumbai)
#
# MANUAL PREREQUISITES (one-time, do this in AWS Console BEFORE running terraform init):
#
# Step 1 — S3 Bucket (ap-south-1):
#   Name:              terraform-state-412628362844
#   Region:            ap-south-1
#   Versioning:        Enabled
#   Block public access: ON (all 4 options)
#
# Step 2 — DynamoDB Table (ap-south-1):
#   Name:              terraform-state-lock
#   Partition key:     LockID  (type: String)
#   Capacity mode:     On-demand (PAY_PER_REQUEST) ← keeps it within free tier
#
# After creating both resources, uncomment the block below and run: terraform init

terraform {
  backend "s3" {
    bucket       = "terraform-state-412628362844"
    key          = "terraform.tfstate"
    region       = "ap-south-1"
    use_lockfile = true # replaces deprecated dynamodb_table — requires S3 versioning enabled
    encrypt      = true
  }
}
