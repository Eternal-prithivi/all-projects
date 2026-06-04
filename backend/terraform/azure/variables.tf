variable "azure_location" {
  type    = string
  default = "eastus"
}

variable "resource_group_name" {
  type    = string
  default = "zenith-rg"
}

variable "enable_azure_storage" {
  type    = bool
  default = false
}

variable "enable_vnet" {
  type    = bool
  default = false
}

variable "enable_azure_vm" {
  type    = bool
  default = false
}

variable "enable_azure_monitor" {
  type    = bool
  default = false
}

variable "enable_cosmos" {
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

variable "instance_name" {
  type    = string
  default = "main-instance"
}

variable "vm_size" {
  type    = string
  default = "Standard_B1s"
}

variable "cosmos_account_name" {
  type    = string
  default = ""
}

variable "cosmos_database_name" {
  type    = string
  default = "zenith-db"
}

variable "alarm_email" {
  type    = string
  default = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}
