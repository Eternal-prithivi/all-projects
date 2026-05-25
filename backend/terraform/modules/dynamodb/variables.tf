variable "enable_dynamodb" {
  description = "Whether to create a DynamoDB table."
  type        = bool
  default     = false
}

variable "table_name" {
  description = "Name of the DynamoDB table."
  type        = string
  default     = ""
}

variable "hash_key" {
  description = "The attribute to use as the hash (partition) key."
  type        = string
  default     = "id"
}

variable "hash_key_type" {
  description = "Type of the hash key attribute (S = String, N = Number, B = Binary)."
  type        = string
  default     = "S"
}

variable "read_capacity" {
  description = "Read capacity units (max 25 for Always Free tier)."
  type        = number
  default     = 5
}

variable "write_capacity" {
  description = "Write capacity units (max 25 for Always Free tier)."
  type        = number
  default     = 5
}

variable "enable_pitr" {
  description = "Enable Point-in-Time Recovery for data backup."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to all resources for cost attribution and governance."
  type        = map(string)
  default     = {}
}
