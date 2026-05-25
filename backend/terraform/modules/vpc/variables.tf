variable "enable_vpc" {
  description = "Whether to create the VPC and associated networking resources."
  type        = bool
  default     = false
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "tags" {
  description = "Tags to apply to all resources for cost attribution and governance."
  type        = map(string)
  default     = {}
}
