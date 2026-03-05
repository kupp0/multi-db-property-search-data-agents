resource "google_sql_database_instance" "postgres" {
  name             = var.cloudsql_pg_instance_id
  database_version = "POSTGRES_15"
  region           = var.region
  project          = google_project.project.project_id

  settings {
    tier    = "db-perf-optimized-N-2"
    edition = "ENTERPRISE_PLUS"
    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.vpc_network.id
      enable_private_path_for_google_cloud_services = true
    }
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = false
    }
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
    database_flags {
      name  = "google_ml_integration.enable_model_support"
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
    command = "gcloud beta sql instances patch ${google_sql_database_instance.postgres.name} --project=${google_project.project.project_id} --data-api-access=ALLOW_DATA_API --enable-google-ml-integration"
  }
}

resource "google_sql_user" "iam_sa_user_pg" {
  name     = trimsuffix(google_service_account.search_backend_sa.email, ".gserviceaccount.com")
  instance = google_sql_database_instance.postgres.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
  project  = google_project.project.project_id
}

resource "google_sql_user" "iam_dev_user_pg" {
  name     = var.developer_email
  instance = google_sql_database_instance.postgres.name
  type     = "CLOUD_IAM_USER"
  project  = google_project.project.project_id
}

resource "google_project_iam_member" "postgres_vertex_ai" {
  project = google_project.project.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_sql_database_instance.postgres.service_account_email_address}"
}
