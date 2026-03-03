resource "google_alloydb_cluster" "default" {
  cluster_id = var.alloydb_cluster_id
  location   = var.region
  project    = google_project.project.project_id

  database_version    = "POSTGRES_17"
  deletion_protection = false
  network_config {
    network = google_compute_network.vpc_network.id
  }

  initial_user {
    user     = "postgres"
    password = var.db_password
  }

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_alloydb_instance" "primary" {
  provider          = google-beta
  cluster           = google_alloydb_cluster.default.name
  instance_id       = var.alloydb_instance_id
  instance_type     = "PRIMARY"
  availability_type = "ZONAL"

  machine_config {
    cpu_count = 2
  }

  database_flags = {
    "alloydb_ai_nl.enabled"                        = "on"
    "google_ml_integration.enable_ai_query_engine" = "on"
    "scann.enable_zero_knob_index_creation"        = "on"
    "password.enforce_complexity"                  = "on"
    "google_db_advisor.enable_auto_advisor"        = "on"
    "google_db_advisor.auto_advisor_schedule"      = "EVERY 24 HOURS"
    "parameterized_views.enabled"                  = "on"
  }

  observability_config {
    enabled                 = true
    max_query_string_length = 10240
    track_wait_event_types  = true
    track_wait_events       = true
    query_plans_per_minute  = 20
    # assistive_experiences_enabled = true # Uncomment if Gemini Cloud Assist is enabled
  }
}
