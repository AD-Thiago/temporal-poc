# Secret Manager Secrets

# Database password secret
resource "google_secret_manager_secret" "db_password" {
  secret_id = "cuida-care-db-password"
  
  replication {
    auto {}
  }
  
  labels = local.common_labels
}

resource "google_secret_manager_secret_version" "db_password_version" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

# Grant Secret Manager access to Cloud Run service account
resource "google_secret_manager_secret_iam_member" "secret_access" {
  secret_id = google_secret_manager_secret.db_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.project_id}@appspot.gserviceaccount.com"
}

# Output
output "db_password_secret_id" {
  value       = google_secret_manager_secret.db_password.secret_id
  description = "Database password secret ID"
}
