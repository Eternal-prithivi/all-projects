variable "azure_location" {
  type    = string
  default = "eastus"
}

variable "enable_azure_storage" {
  type    = bool
  default = false
}

variable "storage_account_name" {
  type    = string
  default = ""
}

variable "container_name" {
  type    = string
  default = "zenith-static"
}

variable "resource_group_name" {
  type    = string
  default = "zenith-rg"
}

variable "tags" {
  type    = map(string)
  default = {}
}
