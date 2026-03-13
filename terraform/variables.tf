variable "project_id" {
  description = "The ID of the Google Cloud project to create"
  type        = string
}

variable "billing_account_id" {
  description = "The Billing Account ID to associate with the project"
  type        = string
}

variable "region" {
  description = "The region for resources"
  type        = string
  default     = "europe-west1"
}

variable "zone" {
  description = "The zone for resources"
  type        = string
  default     = "europe-west1-b"
}

variable "alloydb_cluster_id" {
  description = "The ID of the AlloyDB cluster"
  type        = string
  default     = "search-cluster"
}

variable "alloydb_instance_id" {
  description = "The ID of the AlloyDB primary instance"
  type        = string
  default     = "search-primary"
}

variable "db_password" {
  description = "The password for the AlloyDB postgres user"
  type        = string
  sensitive   = true
}

variable "subnet_cidr" {
  description = "The CIDR block for the subnet"
  type        = string
  default     = "10.0.0.0/24"
}

variable "spanner_instance_id" {
  description = "The ID of the Spanner instance"
  type        = string
  default     = "search-instance"
}

variable "spanner_database_id" {
  description = "The ID of the Spanner database"
  type        = string
  default     = "search-db"
}

variable "cloudsql_pg_instance_id" {
  description = "The ID of the Cloud SQL PostgreSQL instance"
  type        = string
  default     = "search-pg"
}

variable "cloudsql_mysql_instance_id" {
  description = "The ID of the Cloud SQL MySQL instance"
  type        = string
  default     = "search-mysql"
}


variable "developer_email" {
  description = "The email address of the developer for IAM database authentication"
  type        = string
}
