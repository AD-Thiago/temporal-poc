# Cloud Run Services

# Worker HTTP Service
resource "google_cloud_run_v2_service" "worker" {
  name     = "temporal-worker"
  location = var.region
  
  template {
    containers {
      image = "gcr.io/${var.project_id}/temporal-poc-worker:latest"
      
      ports {
        container_port = 8080
      }
      
      env {
        name  = "PORT"
        value = "8080"
      }
      
      env {
        name  = "DATABASE_HOST"
        value = google_sql_database_instance.cuida_care_db.public_ip_address
      }
      
      env {
        name  = "DATABASE_PORT"
        value = "5432"
      }
      
      env {
        name  = "DATABASE_NAME"
        value = "cuida_care"
      }
      
      env {
        name  = "DATABASE_USER"
        value = "app_user"
      }
      
      env {
        name = "DATABASE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
      
      env {
        name  = "INSTANCE_CONNECTION_NAME"
        value = google_sql_database_instance.cuida_care_db.connection_name
      }
      
      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.cuida_care_cache.host
      }
      
      env {
        name  = "REDIS_PORT"
        value = tostring(google_redis_instance.cuida_care_cache.port)
      }
      
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }
      
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
    
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
    
    timeout = "300s"
    
    vpc_access {
      connector = google_vpc_access_connector.cuida_vpc_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }
  
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  
  labels = local.common_labels
  
  depends_on = [
    google_sql_database_instance.cuida_care_db,
    google_redis_instance.cuida_care_cache,
    google_vpc_access_connector.cuida_vpc_connector
  ]
}

# FastAPI Service
resource "google_cloud_run_v2_service" "api" {
  name     = "cuida-care-api"
  location = var.region
  
  template {
    containers {
      image = "gcr.io/${var.project_id}/cuida-care-api:latest"
      
      ports {
        container_port = 8080
      }
      
      env {
        name  = "PORT"
        value = "8080"
      }
      
      env {
        name  = "DATABASE_HOST"
        value = google_sql_database_instance.cuida_care_db.public_ip_address
      }
      
      env {
        name  = "DATABASE_PORT"
        value = "5432"
      }
      
      env {
        name  = "DATABASE_NAME"
        value = "cuida_care"
      }
      
      env {
        name  = "DATABASE_USER"
        value = "app_user"
      }
      
      env {
        name = "DATABASE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
      
      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.cuida_care_cache.host
      }
      
      env {
        name  = "REDIS_PORT"
        value = tostring(google_redis_instance.cuida_care_cache.port)
      }
      
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }
      
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
    
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
    
    timeout = "60s"
    
    vpc_access {
      connector = google_vpc_access_connector.cuida_vpc_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }
  
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  
  labels = local.common_labels
  
  depends_on = [
    google_sql_database_instance.cuida_care_db,
    google_redis_instance.cuida_care_cache,
    google_vpc_access_connector.cuida_vpc_connector
  ]
}

# IAM for unauthenticated access
resource "google_cloud_run_service_iam_member" "worker_noauth" {
  service  = google_cloud_run_v2_service.worker.name
  location = google_cloud_run_v2_service.worker.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "api_noauth" {
  service  = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "worker_url" {
  value       = google_cloud_run_v2_service.worker.uri
  description = "Worker service URL"
}

output "api_url" {
  value       = google_cloud_run_v2_service.api.uri
  description = "API service URL"
}
