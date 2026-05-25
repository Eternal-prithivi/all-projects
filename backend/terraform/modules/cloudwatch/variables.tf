variable "enable_cloudwatch" {
  description = "Whether to create CloudWatch alarms and SNS notifications."
  type        = bool
  default     = false
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarm notifications."
  type        = string
  default     = ""
}

variable "instance_id" {
  description = "EC2 instance ID to monitor. Set to null if EC2 is not enabled."
  type        = string
  default     = null
}

variable "enable_ec2" {
  description = "Whether EC2 is enabled. CPU alarm is only created when both CloudWatch and EC2 are enabled."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to all resources for cost attribution and governance."
  type        = map(string)
  default     = {}
}
