resource "google_sql_database_instance" "mysql" {
  name             = var.cloudsql_mysql_instance_id
  database_version = "MYSQL_8_4"
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
      name  = "cloudsql_iam_authentication"
      value = "on"
    }
    database_flags {
      name  = "cloudsql_vector"
      value = "on"
    }
    database_flags {
      name  = "cloudsql.enable_google_ml_integration"
      value = "on"
    }
  }
  deletion_protection = false
}

resource "google_sql_database" "mysql_db" {
  name     = "search"
  instance = google_sql_database_instance.mysql.name
  project  = google_project.project.project_id
}

resource "google_sql_user" "mysql_user" {
  name     = "mysql"
  instance = google_sql_database_instance.mysql.name
  password = var.db_password
  project  = google_project.project.project_id
}

resource "null_resource" "enable_data_api_mysql" {
  triggers = {
    instance_id = google_sql_database_instance.mysql.name
  }

  provisioner "local-exec" {
    command = "gcloud beta sql instances patch ${google_sql_database_instance.mysql.name} --project=${google_project.project.project_id} --data-api-access=ALLOW_DATA_API"
  }
}

resource "null_resource" "enable_ml_integration_mysql" {
  triggers = {
    instance_id = google_sql_database_instance.mysql.name
  }

  provisioner "local-exec" {
    command = "gcloud beta sql instances patch ${google_sql_database_instance.mysql.name} --project=${google_project.project.project_id} --enable-google-ml-integration"
  }
  depends_on = [null_resource.enable_data_api_mysql]
}

resource "google_sql_user" "iam_sa_user_mysql" {
  # For type = "CLOUD_IAM_SERVICE_ACCOUNT", the API expects the full email address.
  # Cloud SQL for MySQL will internally truncate the @ and domain name.
  name     = google_service_account.search_backend_sa.email
  instance = google_sql_database_instance.mysql.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
  project  = google_project.project.project_id
}

resource "google_sql_user" "iam_dev_user_mysql" {
  name     = var.developer_email
  instance = google_sql_database_instance.mysql.name
  type     = "CLOUD_IAM_USER"
  project  = google_project.project.project_id
}

resource "google_project_iam_member" "mysql_vertex_ai" {
  project = google_project.project.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_sql_database_instance.mysql.service_account_email_address}"
}
