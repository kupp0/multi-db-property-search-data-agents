resource "time_sleep" "wait_for_iam" {
  depends_on      = [google_project_service.services]
  create_duration = "30s"
}

resource "google_storage_bucket" "images_bucket" {
  name          = "property-images-data-agent-${var.project_id}-v2"
  project       = google_project.project.project_id
  location      = var.region
  force_destroy = true
  depends_on    = [time_sleep.wait_for_iam]

  uniform_bucket_level_access = true

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}


