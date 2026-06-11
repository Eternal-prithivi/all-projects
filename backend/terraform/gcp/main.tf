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

# --- Cloud Storage (static site) ---
resource "google_storage_bucket" "static_site" {
  count    = var.enable_gcs && var.bucket_name != "" ? 1 : 0
  name     = var.bucket_name
  location = var.gcp_region

  uniform_bucket_level_access = true
  force_destroy               = true
  labels                      = var.tags
}

# --- VPC network ---
resource "google_compute_network" "vpc" {
  count                   = var.enable_gcp_network ? 1 : 0
  name                    = "zenith-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  count         = var.enable_gcp_network ? 1 : 0
  name          = "zenith-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.gcp_region
  network       = google_compute_network.vpc[0].id
}

# --- Compute Engine ---
resource "google_compute_instance" "app" {
  count        = var.enable_gce && var.enable_gcp_network ? 1 : 0
  name         = var.instance_name
  machine_type = var.machine_type
  zone         = "${var.gcp_region}-a"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = var.disk_size_gb
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.subnet[0].id
    access_config {}
  }

  labels = var.tags

  depends_on = [google_compute_subnetwork.subnet]
}

# --- Service account (IAM) ---
resource "google_service_account" "app" {
  count        = var.enable_gcp_service_account ? 1 : 0
  account_id   = var.service_account_id
  display_name = "Zenith provisioned app service account"
}

resource "google_project_iam_member" "storage_viewer" {
  count   = var.enable_gcp_service_account && var.enable_gcs ? 1 : 0
  project = var.gcp_project
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.app[0].email}"
}

# --- Monitoring alert (email channel when address set) ---
resource "google_monitoring_notification_channel" "email" {
  count        = var.enable_gcp_monitoring && var.alarm_email != "" ? 1 : 0
  display_name = "Zenith Email"
  type         = "email"
  labels = {
    email_address = var.alarm_email
  }
}

resource "google_monitoring_alert_policy" "instance_cpu" {
  count        = var.enable_gcp_monitoring && var.enable_gce ? 1 : 0
  display_name = "Zenith GCE CPU alert"
  combiner     = "OR"

  conditions {
    display_name = "CPU utilization"
    condition_threshold {
      filter          = "resource.type = \"gce_instance\" AND metric.type = \"compute.googleapis.com/instance/cpu/utilization\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.85
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.alarm_email != "" ? [google_monitoring_notification_channel.email[0].name] : []

  depends_on = [google_compute_instance.app]
}

# --- Firestore (serverless NoSQL) ---
resource "google_firestore_database" "main" {
  count       = var.enable_firestore ? 1 : 0
  project     = var.gcp_project
  name        = var.firestore_database_id
  location_id = var.gcp_region
  type        = "FIRESTORE_NATIVE"
}

output "gcs_bucket_url" {
  value = length(google_storage_bucket.static_site) > 0 ? "gs://${google_storage_bucket.static_site[0].name}" : ""
}

output "gce_instance_name" {
  value = length(google_compute_instance.app) > 0 ? google_compute_instance.app[0].name : ""
}

output "firestore_database" {
  value = length(google_firestore_database.main) > 0 ? google_firestore_database.main[0].name : ""
}
