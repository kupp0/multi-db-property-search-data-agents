resource "google_sql_database_instance" "postgres" {
  name             = var.cloudsql_pg_instance_id
  database_version = "POSTGRES_15"
  region           = var.region
  project          = google_project.project.project_id

  settings {
    tier    = "db-custom-2-8192"
    edition = "ENTERPRISE_PLUS"
    ip_configuration {
      ipv4_enabled = false
      psc_config {
        psc_enabled               = true
        allowed_consumer_projects = [google_project.project.project_id]
      }
    }
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }
  deletion_protection = false
}

resource "google_sql_database" "postgres_db" {
  name     = "search"
  instance = google_sql_database_instance.postgres.name
  project  = google_project.project.project_id
}

resource "google_sql_user" "postgres_user" {
  name     = "postgres"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
  project  = google_project.project.project_id
}

resource "null_resource" "enable_data_api_pg" {
  triggers = {
    instance_id = google_sql_database_instance.postgres.name
  }

  provisioner "local-exec" {
    command = "gcloud beta sql instances patch ${google_sql_database_instance.postgres.name} --project=${google_project.project.project_id} --data-api-access=ALLOW_DATA_API"
  }
}
