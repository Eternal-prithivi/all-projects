output "sns_topic_arn" {
  description = "ARN of the CloudWatch alerts SNS topic."
  value       = var.enable_cloudwatch ? aws_sns_topic.alerts[0].arn : null
}

output "alarm_name" {
  description = "Name of the CPU utilization CloudWatch alarm."
  value       = var.enable_cloudwatch && var.instance_id != null ? aws_cloudwatch_metric_alarm.cpu_high[0].alarm_name : null
}
