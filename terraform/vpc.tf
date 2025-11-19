# VPC Connector for Cloud Run private networking

resource "google_vpc_access_connector" "cuida_vpc_connector" {
  name          = "cuida-vpc-connector"
  region        = var.region
  ip_cidr_range = "10.9.0.0/28"
  network       = "default"
  
  min_instances = 2
  max_instances = 3
  machine_type  = "e2-micro"
  
  # Depends on the VPC network
  # network = google_compute_network.vpc_network.name
}

output "vpc_connector_name" {
  value       = google_vpc_access_connector.cuida_vpc_connector.name
  description = "VPC Connector name"
}

output "vpc_connector_id" {
  value       = google_vpc_access_connector.cuida_vpc_connector.id
  description = "VPC Connector ID"
}
