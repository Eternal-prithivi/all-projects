variable "gcp_project" {
  type    = string
  default = ""
}

variable "gcp_region" {
  type    = string
  default = "us-central1"
}

variable "enable_gcs" {
  type    = bool
  default = false
}

variable "enable_gcp_network" {
  type    = bool
  default = false
}

variable "enable_gce" {
  type    = bool
  default = false
}

variable "enable_gcp_service_account" {
  type    = bool
  default = false
}

variable "enable_gcp_monitoring" {
  type    = bool
  default = false
}

variable "enable_firestore" {
  type    = bool
  default = false
}

variable "bucket_name" {
  type    = string
  default = ""
}

variable "instance_name" {
  type    = string
  default = "main-instance"
}

variable "machine_type" {
  type    = string
  default = "e2-micro"
}

variable "service_account_id" {
  type    = string
  default = "zenith-app-sa"
}

variable "firestore_database_id" {
  type    = string
  default = "(default)"
}

variable "alarm_email" {
  type    = string
  default = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "disk_size_gb" {
  type    = number
  default = 30
}
