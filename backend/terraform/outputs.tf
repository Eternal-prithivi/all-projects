# outputs.tf — Deployment Outputs
# Displayed after successful terraform apply

output "vpc_id" {
  description = "ID of the created VPC."
  value       = var.enable_vpc ? module.vpc.vpc_id : null
}

output "public_subnet_id" {
  description = "ID of the public subnet."
  value       = var.enable_vpc ? module.vpc.public_subnet_id : null
}

output "ec2_public_ip" {
  description = "Public IP address of the EC2 instance."
  value       = var.enable_ec2 ? module.ec2.public_ip : null
}

output "ec2_instance_id" {
  description = "Instance ID of the EC2 instance."
  value       = var.enable_ec2 ? module.ec2.instance_id : null
}

output "s3_bucket_name" {
  description = "Name of the created S3 bucket."
  value       = var.enable_s3 ? module.s3.bucket_name : null
}

output "s3_bucket_arn" {
  description = "ARN of the created S3 bucket."
  value       = var.enable_s3 ? module.s3.bucket_arn : null
}

output "iam_role_arn" {
  description = "ARN of the created IAM role."
  value       = var.enable_iam ? module.iam.role_arn : null
}

output "dynamodb_table_name" {
  description = "Name of the created DynamoDB table."
  value       = var.enable_dynamodb ? module.dynamodb.dynamodb_table_name : null
}

output "dynamodb_table_arn" {
  description = "ARN of the created DynamoDB table."
  value       = var.enable_dynamodb ? module.dynamodb.dynamodb_table_arn : null
}
