terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  region = var.region
}

provider "google-beta" {
  region = var.region
}

# Project Creation
resource "google_project" "project" {
  name            = var.project_id
  project_id      = var.project_id
  billing_account = var.billing_account_id
  # folder_id       = "..." # Optional: Add if needed
}

# Enable Services
resource "google_project_service" "services" {
  for_each = toset([
    "alloydb.googleapis.com",
    "compute.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "aiplatform.googleapis.com",
    "servicenetworking.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "orgpolicy.googleapis.com",
    "cloudaicompanion.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
    "secretmanager.googleapis.com",
    "geminidataanalytics.googleapis.com",
    "sqladmin.googleapis.com",
    "spanner.googleapis.com",
    "storage.googleapis.com",
    "iap.googleapis.com"
  ])

  project = google_project.project.project_id
  service = each.key

  disable_on_destroy = false
}

# VPC Network
resource "google_compute_network" "vpc_network" {
  name                    = "search-demo-vpc"
  project                 = google_project.project.project_id
  auto_create_subnetworks = false
  depends_on              = [google_project_service.services]
}

# Subnet
resource "google_compute_subnetwork" "default" {
  name          = "search-demo-vpc" # Must match service.yaml expectations
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc_network.id
  project       = google_project.project.project_id

  private_ip_google_access = true
}

# IAP SSH Firewall Rule
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "allow-iap-ssh"
  network = google_compute_network.vpc_network.id
  project = google_project.project.project_id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"]
}

# Private Service Access for AlloyDB
resource "google_compute_global_address" "private_ip_address" {
  name          = "alloydb-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
  project       = google_project.project.project_id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
  depends_on              = [google_project_service.services]
}