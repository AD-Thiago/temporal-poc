# Pub/Sub Topics and Subscriptions

# Main topic for job processing
resource "google_pubsub_topic" "hello_topic" {
  name = "hello-topic"
  
  message_retention_duration = "86400s"  # 24 hours
  
  labels = local.common_labels
}

# Dead Letter Queue topic
resource "google_pubsub_topic" "dlq_topic" {
  name = "hello-topic-dlq"
  
  message_retention_duration = "604800s"  # 7 days
  
  labels = local.common_labels
}

# Push subscription to Cloud Run worker
resource "google_pubsub_subscription" "worker_subscription" {
  name  = "hello-subscription"
  topic = google_pubsub_topic.hello_topic.id
  
  ack_deadline_seconds = 600  # 10 minutes
  
  push_config {
    push_endpoint = "${google_cloud_run_v2_service.worker.uri}/pubsub/push"
    
    oidc_token {
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
    }
    
    attributes = {
      x-goog-version = "v1"
    }
  }
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq_topic.id
    max_delivery_attempts = 5
  }
  
  expiration_policy {
    ttl = ""  # Never expire
  }
  
  labels = local.common_labels
  
  depends_on = [google_cloud_run_v2_service.worker]
}

# IAM for Pub/Sub to invoke Cloud Run
resource "google_project_iam_member" "pubsub_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# Grant Pub/Sub permission to publish to DLQ
resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  topic  = google_pubsub_topic.dlq_topic.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# Get project number
data "google_project" "project" {
  project_id = var.project_id
}

# Outputs
output "main_topic_id" {
  value       = google_pubsub_topic.hello_topic.id
  description = "Main Pub/Sub topic ID"
}

output "dlq_topic_id" {
  value       = google_pubsub_topic.dlq_topic.id
  description = "Dead Letter Queue topic ID"
}

output "subscription_id" {
  value       = google_pubsub_subscription.worker_subscription.id
  description = "Pub/Sub subscription ID"
}
