output "bucket_name" {
  description = "Name of the created S3 bucket."
  value       = var.enable_s3 ? aws_s3_bucket.main[0].bucket : null
}

output "bucket_arn" {
  description = "ARN of the created S3 bucket."
  value       = var.enable_s3 ? aws_s3_bucket.main[0].arn : null
}
