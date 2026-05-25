variable "budget_limit" {
  description = "Monthly budget limit in USD. An alert fires when this amount is reached."
  type        = string
  default     = "1"
}

variable "budget_email" {
  description = "Email address to receive billing alerts."
  type        = string
}
