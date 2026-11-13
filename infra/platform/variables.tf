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

variable "state_bucket" {
  description = "S3 bucket that stores the Terraform state of infra/terraform and infra/platform."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.state_bucket))
    error_message = "state_bucket must be a valid S3 bucket name."
  }
}

variable "infra_state_key" {
  description = "S3 key of the infra/terraform state read through terraform_remote_state."
  type        = string
  default     = "withdrawal-soles/infra.tfstate"
}

variable "wallet_service_url" {
  description = "Base URL of the PEN wallet (billetera-api) consumed for debits and reversals. Defaults to the in-cluster Service of the shared EKS cluster. Ignored when wallet_mock_enabled is true."
  type        = string
  default     = "http://billetera-api.billetera.svc.cluster.local:3000"

  validation {
    condition     = can(regex("^https?://", var.wallet_service_url))
    error_message = "wallet_service_url must start with http:// or https://."
  }
}

variable "wallet_mock_enabled" {
  description = "Route /v1/ wallet calls to the mock-dependencies stub through Traefik instead of billetera-api. Keep false in the shared cluster."
  type        = bool
  default     = false
}

variable "mock_dependencies_enabled" {
  description = "Deploy the mock-dependencies stub that serves /usuarios, /api/v1/accounts, and /api/v1/transactions. When false, set the service URL overrides to real services."
  type        = bool
  default     = true
}

variable "user_service_url" {
  description = "Override for WITHDRAWAL_SOLES_USER_SERVICE_URL. Empty uses the in-cluster Traefik gateway."
  type        = string
  default     = ""
}

variable "users_service_url" {
  description = "Override for WITHDRAWAL_SOLES_USERS_SERVICE_URL (GET /usuarios/{id}). Empty falls back to user_service_url inside the application."
  type        = string
  default     = ""
}

variable "transaction_service_url" {
  description = "Override for WITHDRAWAL_SOLES_TRANSACTION_SERVICE_URL. Empty uses the in-cluster Traefik gateway."
  type        = string
  default     = ""
}

variable "jwt_secret" {
  description = "Shared HS256 service JWT secret. Must equal JWT_SECRET in billetera-api. Supply through TF_VAR_jwt_secret; never commit it."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.jwt_secret) >= 16
    error_message = "jwt_secret must be at least 16 characters."
  }
}

variable "jwt_issuer" {
  description = "Service JWT issuer shared with billetera-api (JWT_ISSUER)."
  type        = string
  default     = "billetera-dev"
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
