variable "aws_region" {
  description = "AWS region used by the EKS cluster."
  type        = string
  default     = "us-east-1"
}

variable "namespace" {
  description = "Kubernetes namespace for the application workloads."
  type        = string
  default     = "withdrawal-soles"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,40}$", var.namespace))
    error_message = "namespace must be a valid lowercase Kubernetes namespace."
  }
}

variable "traefik_namespace" {
  description = "Kubernetes namespace for Traefik."
  type        = string
  default     = "traefik"
}

variable "traefik_chart_version" {
  description = "Pinned Traefik Helm chart version."
  type        = string
  default     = "42.2.0"
}

variable "traefik_replicas" {
  description = "Number of Traefik replicas."
  type        = number
  default     = 2

  validation {
    condition     = var.traefik_replicas >= 1 && var.traefik_replicas <= 3
    error_message = "traefik_replicas must be between 1 and 3."
  }
}

variable "app_replicas" {
  description = "Number of withdrawal-soles replicas."
  type        = number
  default     = 2

  validation {
    condition     = var.app_replicas >= 1 && var.app_replicas <= 3
    error_message = "app_replicas must be between 1 and 3."
  }
}

variable "mock_replicas" {
  description = "Number of mock dependency replicas."
  type        = number
  default     = 1
}

variable "image_tag" {
  description = "Immutable image tag pushed to the ECR repository."
  type        = string
  default     = "latest"
}

variable "image_pull_policy" {
  description = "Kubernetes image pull policy."
  type        = string
  default     = "IfNotPresent"

  validation {
    condition     = contains(["Always", "IfNotPresent", "Never"], var.image_pull_policy)
    error_message = "image_pull_policy must be Always, IfNotPresent, or Never."
  }
}

variable "wallet_service_url" {
  description = "Base URL of the published PEN wallet API consumed for debits and reversals."
  type        = string
  default     = "http://52.67.162.209"
}

variable "db_username" {
  description = "PostgreSQL user for the application."
  type        = string
  default     = "withdrawal"
}

variable "db_password" {
  description = "PostgreSQL password. Supply through TF_VAR_db_password or an ignored terraform.tfvars."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 12
    error_message = "db_password must be at least 12 characters."
  }
}
