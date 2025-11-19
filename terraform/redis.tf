# Cloud Memorystore Redis Instance

resource "google_redis_instance" "cuida_care_cache" {
  name           = "cuida-care-cache"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region
  
  redis_version     = "REDIS_7_0"
  display_name      = "CUIDA+Care Command Center Cache"
  reserved_ip_range = "10.168.202.0/29"
  
  auth_enabled = false
  transit_encryption_mode = "DISABLED"
  
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
      }
    }
  }
  
  redis_configs = {
    maxmemory-policy = "allkeys-lru"
    notify-keyspace-events = "Ex"
  }
  
  labels = local.common_labels
}

# Output
output "redis_host" {
  value       = google_redis_instance.cuida_care_cache.host
  description = "Redis instance host IP"
}

output "redis_port" {
  value       = google_redis_instance.cuida_care_cache.port
  description = "Redis instance port"
}

output "redis_current_location_id" {
  value       = google_redis_instance.cuida_care_cache.current_location_id
  description = "Redis instance location"
}
