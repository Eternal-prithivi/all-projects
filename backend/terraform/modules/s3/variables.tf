variable "enable_s3" {
  description = "Whether to create an S3 bucket."
  type        = bool
  default     = false
}

variable "bucket_name" {
  description = "Name for the S3 bucket. Must be globally unique."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources for cost attribution and governance."
  type        = map(string)
  default     = {}
}
