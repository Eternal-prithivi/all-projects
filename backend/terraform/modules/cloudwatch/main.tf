# modules/cloudwatch/main.tf — CloudWatch SNS + CPU Alarm for EC2

resource "aws_sns_topic" "alerts" {
  count = var.enable_cloudwatch ? 1 : 0
  name  = "cloudwatch-alerts"

  tags = var.tags
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.enable_cloudwatch && var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  count               = var.enable_cloudwatch && var.enable_ec2 ? 1 : 0
  alarm_name          = "ec2-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "EC2 CPU utilization exceeded 80% for 10 minutes."
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    InstanceId = var.instance_id
  }

  tags = var.tags
}
