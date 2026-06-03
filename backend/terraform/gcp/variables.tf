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

variable "bucket_name" {
  type    = string
  default = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}
