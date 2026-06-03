terraform {
  required_version = ">= 1.10.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

resource "google_storage_bucket" "static_site" {
  count    = var.enable_gcs && var.bucket_name != "" ? 1 : 0
  name     = var.bucket_name
  location = var.gcp_region

  uniform_bucket_level_access = true
  force_destroy               = true

  labels = var.tags
}

output "gcs_bucket_url" {
  value = length(google_storage_bucket.static_site) > 0 ? "gs://${google_storage_bucket.static_site[0].name}" : ""
}
