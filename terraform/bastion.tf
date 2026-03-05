resource "google_service_account" "bastion_sa" {
  account_id   = "bastion-sa"
  display_name = "Bastion Host Service Account"
  project      = google_project.project.project_id
}

resource "google_project_iam_member" "bastion_alloydb_client" {
  project = google_project.project.project_id
  role    = "roles/alloydb.client"
  member  = "serviceAccount:${google_service_account.bastion_sa.email}"
}

resource "google_project_iam_member" "bastion_cloudsql_client" {
  project = google_project.project.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.bastion_sa.email}"
}

resource "google_project_iam_member" "bastion_service_usage" {
  project = google_project.project.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${google_service_account.bastion_sa.email}"
}

resource "google_project_iam_member" "bastion_compute_network_admin" {
  project = google_project.project.project_id
  role    = "roles/compute.networkAdmin"
  member  = "serviceAccount:${google_service_account.bastion_sa.email}"
}

resource "google_compute_instance" "bastion" {
  name         = "db-bastion"
  machine_type = "e2-micro"
  zone         = "${var.region}-b"
  project      = google_project.project.project_id

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  network_interface {
    network    = google_compute_network.vpc_network.id
    subnetwork = google_compute_subnetwork.default.id
    # No access_config block means no public IP
  }

  service_account {
    email  = google_service_account.bastion_sa.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    enable-oslogin = "TRUE"
    alloydb_uri    = "projects/${google_project.project.project_id}/locations/${var.region}/clusters/${google_alloydb_cluster.default.cluster_id}/instances/${google_alloydb_instance.primary.instance_id}"
    cloudsql_uri   = "${google_project.project.project_id}:${var.region}:${google_sql_database_instance.postgres.name}"
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    # Install proxies
    wget https://storage.googleapis.com/alloydb-auth-proxy/v1.12.0/alloydb-auth-proxy.linux.amd64 -O /usr/local/bin/alloydb-auth-proxy
    chmod +x /usr/local/bin/alloydb-auth-proxy

    wget https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.11.0/cloud-sql-proxy.linux.amd64 -O /usr/local/bin/cloud-sql-proxy
    chmod +x /usr/local/bin/cloud-sql-proxy

    # Get URIs from metadata
    ALLOYDB_URI=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/alloydb_uri" -H "Metadata-Flavor: Google")
    CLOUDSQL_URI=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/cloudsql_uri" -H "Metadata-Flavor: Google")

    # Create systemd services
    cat <<EOT > /etc/systemd/system/alloydb-proxy.service
    [Unit]
    Description=AlloyDB Auth Proxy
    After=network.target

    [Service]
    Type=simple
    ExecStart=/usr/local/bin/alloydb-auth-proxy $${ALLOYDB_URI} --address 127.0.0.1 --port 5432
    Restart=always
    User=nobody

    [Install]
    WantedBy=multi-user.target
    EOT

    cat <<EOT > /etc/systemd/system/cloudsql-proxy.service
    [Unit]
    Description=Cloud SQL Auth Proxy
    After=network.target

    [Service]
    Type=simple
    ExecStart=/usr/local/bin/cloud-sql-proxy $${CLOUDSQL_URI} --address 127.0.0.1 --port 5433 --private-ip
    Restart=always
    User=nobody

    [Install]
    WantedBy=multi-user.target
    EOT

    systemctl daemon-reload
    systemctl enable alloydb-proxy
    systemctl start alloydb-proxy
    systemctl enable cloudsql-proxy
    systemctl start cloudsql-proxy
  EOF

  depends_on = [
    google_project_service.services,
    google_alloydb_instance.primary,
    google_sql_database_instance.postgres
  ]
}
