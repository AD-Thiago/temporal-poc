# Cloud SQL PostgreSQL Instance

resource "google_sql_database_instance" "cuida_care_db" {
  name             = "cuida-care-db"
  database_version = "POSTGRES_15"
  region           = var.region
  
  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_type         = "PD_SSD"
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }
    
    ip_configuration {
      ipv4_enabled    = true
      private_network = null
      require_ssl     = false
    }
    
    maintenance_window {
      day          = 7  # Sunday
      hour         = 3
      update_track = "stable"
    }
    
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
    
    database_flags {
      name  = "max_connections"
      value = "100"
    }
    
    database_flags {
      name  = "shared_buffers"
      value = "32768"  # 256MB in 8KB pages
    }
  }
  
  deletion_protection = true
  
  labels = local.common_labels
}

# Database
resource "google_sql_database" "cuida_care" {
  name     = "cuida_care"
  instance = google_sql_database_instance.cuida_care_db.name
}

# Database User
resource "google_sql_user" "app_user" {
  name     = "app_user"
  instance = google_sql_database_instance.cuida_care_db.name
  password = var.db_password
}

# Outputs
output "database_instance_name" {
  value       = google_sql_database_instance.cuida_care_db.name
  description = "Cloud SQL instance name"
}

output "database_connection_name" {
  value       = google_sql_database_instance.cuida_care_db.connection_name
  description = "Cloud SQL connection name"
}

output "database_ip" {
  value       = google_sql_database_instance.cuida_care_db.public_ip_address
  description = "Cloud SQL public IP"
}
