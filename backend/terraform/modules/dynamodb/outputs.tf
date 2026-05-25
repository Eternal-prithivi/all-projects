output "dynamodb_table_name" {
  description = "Name of the created DynamoDB table."
  value       = var.enable_dynamodb ? aws_dynamodb_table.main[0].name : null
}

output "dynamodb_table_arn" {
  description = "ARN of the created DynamoDB table."
  value       = var.enable_dynamodb ? aws_dynamodb_table.main[0].arn : null
}
