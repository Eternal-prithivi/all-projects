variable "enable_iam" {
  description = "Whether to create an IAM role."
  type        = bool
  default     = false
}

variable "role_name" {
  description = "Name for the IAM role."
  type        = string
  default     = "app-role"
}

variable "s3_bucket_name" {
  description = "S3 bucket name the IAM role will have read access to."
  type        = string
  default     = "*"
}

variable "tags" {
  description = "Tags to apply to all resources for cost attribution and governance."
  type        = map(string)
  default     = {}
}
