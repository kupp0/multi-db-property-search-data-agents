resource "google_spanner_instance" "main" {
  name         = var.spanner_instance_id
  config           = "regional-${var.region}"
  display_name     = "Property Search Spanner"
  processing_units = 100
  project      = google_project.project.project_id
  depends_on   = [google_project_service.services]
}

resource "google_spanner_database" "database" {
  instance         = google_spanner_instance.main.name
  name             = var.spanner_database_id
  project          = google_project.project.project_id
  database_dialect = "POSTGRESQL"
}
