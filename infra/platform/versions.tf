terraform {
  required_version = ">= 1.10.0, < 2.0.0"

  # Partial S3 backend. Bucket, key, and region come from scripts/tf-init.sh
  # (or -backend-config) so the same code works for operators and CI.
  backend "s3" {}

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 3.0"
    }
  }
}
