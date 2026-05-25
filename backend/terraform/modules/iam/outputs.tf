output "role_arn" {
  description = "ARN of the created IAM role."
  value       = var.enable_iam ? aws_iam_role.main[0].arn : null
}

output "role_name" {
  description = "Name of the created IAM role."
  value       = var.enable_iam ? aws_iam_role.main[0].name : null
}

output "instance_profile_name" {
  description = "Name of the IAM instance profile."
  value       = var.enable_iam ? aws_iam_instance_profile.main[0].name : null
}
