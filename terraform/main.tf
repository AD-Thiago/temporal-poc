# CUIDA+Care Command Center - Terraform Infrastructure
# Complete infrastructure as code

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  # Backend configuration for remote state
  backend "gcs" {
    bucket = "cuida-care-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "adc-agent"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (production/staging/development)"
  type        = string
  default     = "production"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# Locals
locals {
  common_labels = {
    project     = "cuida-care"
    environment = var.environment
    managed_by  = "terraform"
  }
}
