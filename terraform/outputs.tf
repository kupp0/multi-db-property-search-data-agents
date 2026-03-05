output "project_id" {
  value = var.project_id
}

output "region" {
  value = var.region
}



output "alloydb_cluster_id" {
  value = var.alloydb_cluster_id
}

output "alloydb_instance_id" {
  value = var.alloydb_instance_id
}

output "alloydb_cluster_ip" {
  value = google_compute_global_address.private_ip_address.address
}


output "alloydb_sa_email" {
  value = google_project_service_identity.alloydb_sa.email
}

output "db_host" {
  value = google_alloydb_instance.primary.ip_address
}

output "db_pass" {
  value     = var.db_password
  sensitive = true
}

output "instance_connection_name" {
  description = "The connection name of the AlloyDB instance to be used in env vars"
  value       = "projects/${var.project_id}/locations/${var.region}/clusters/${var.alloydb_cluster_id}/instances/${var.alloydb_instance_id}"
}

output "spanner_instance_id" {
  value = var.spanner_instance_id
}

output "spanner_database_id" {
  value = var.spanner_database_id
}

output "cloudsql_pg_instance_id" {
  value = var.cloudsql_pg_instance_id
}
