resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = var.namespace

    labels = {
      "app.kubernetes.io/part-of" = "withdrawal-soles"
    }
  }
}

resource "kubernetes_secret_v1" "database" {
  metadata {
    name      = "withdrawal-db"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  type = "Opaque"

  data = {
    url = local.database_url
  }
}

resource "kubernetes_secret_v1" "jwt" {
  metadata {
    name      = "withdrawal-jwt"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  type = "Opaque"

  data = {
    secret = var.jwt_secret
  }
}

resource "kubernetes_job_v1" "migrate" {
  metadata {
    name      = "withdrawal-migrate"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  spec {
    backoff_limit              = 3
    ttl_seconds_after_finished = 600

    template {
      metadata {
        labels = {
          "app.kubernetes.io/name" = "withdrawal-migrate"
        }
      }

      spec {
        restart_policy = "Never"

        container {
          name              = "migrate"
          image             = local.image_uri
          image_pull_policy = var.image_pull_policy
          command           = ["alembic", "upgrade", "head"]

          env {
            name = "WITHDRAWAL_SOLES_DATABASE_URL"

            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.database.metadata[0].name
                key  = "url"
              }
            }
          }
        }
      }
    }
  }

  wait_for_completion = true

  depends_on = [kubernetes_secret_v1.database]

  lifecycle {
    replace_triggered_by = [kubernetes_secret_v1.database]
  }
}

resource "kubernetes_deployment_v1" "app" {
  metadata {
    name      = local.app_name
    namespace = kubernetes_namespace_v1.app.metadata[0].name

    labels = {
      "app.kubernetes.io/name"    = local.app_name
      "app.kubernetes.io/part-of" = "withdrawal-soles"
    }
  }

  spec {
    replicas = var.app_replicas

    selector {
      match_labels = {
        "app.kubernetes.io/name" = local.app_name
      }
    }

    template {
      metadata {
        labels = {
          "app.kubernetes.io/name"    = local.app_name
          "app.kubernetes.io/part-of" = "withdrawal-soles"
        }

        # Bump jwt_secret_version when rotating jwt_secret to restart the pods.
        # The value must be known at plan time: a computed value such as the
        # Secret's resource_version makes the kubernetes provider fail with
        # "Provider produced inconsistent final plan". A hash of the secret
        # would also work but would publish a guessable digest in pod metadata.
        annotations = {
          "withdrawal-soles/jwt-secret-version" = var.jwt_secret_version
        }
      }

      spec {
        container {
          name              = local.app_name
          image             = local.image_uri
          image_pull_policy = var.image_pull_policy
          command           = ["uvicorn", "withdrawal_soles.main:app", "--host", "0.0.0.0", "--port", "8000"]

          port {
            container_port = 8000
            name           = "http"
          }

          env {
            name = "WITHDRAWAL_SOLES_DATABASE_URL"

            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.database.metadata[0].name
                key  = "url"
              }
            }
          }

          dynamic "env" {
            for_each = local.app_env

            content {
              name  = env.key
              value = env.value
            }
          }

          dynamic "env" {
            for_each = toset(local.jwt_secret_env)

            content {
              name = env.value

              value_from {
                secret_key_ref {
                  name = kubernetes_secret_v1.jwt.metadata[0].name
                  key  = "secret"
                }
              }
            }
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "128Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "512Mi"
            }
          }

          readiness_probe {
            http_get {
              path = "/health"
              port = 8000
            }

            initial_delay_seconds = 10
            period_seconds        = 5
            timeout_seconds       = 3
            failure_threshold     = 6
          }

          liveness_probe {
            http_get {
              path = "/health"
              port = 8000
            }

            initial_delay_seconds = 30
            period_seconds        = 10
            timeout_seconds       = 3
            failure_threshold     = 3
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_job_v1.migrate,
    helm_release.traefik,
  ]

  lifecycle {
    precondition {
      condition     = var.mock_dependencies_enabled || !var.wallet_mock_enabled
      error_message = "wallet_mock_enabled requires mock_dependencies_enabled = true."
    }

    precondition {
      condition     = var.mock_dependencies_enabled || (var.user_service_url != "" && var.transaction_service_url != "")
      error_message = "When mock_dependencies_enabled is false, set user_service_url and transaction_service_url to real services."
    }
  }
}

resource "kubernetes_service_v1" "app" {
  metadata {
    name      = local.app_name
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  spec {
    selector = {
      "app.kubernetes.io/name" = local.app_name
    }

    port {
      name        = "http"
      port        = 80
      target_port = 8000
      protocol    = "TCP"
    }
  }
}

resource "kubernetes_deployment_v1" "mock" {
  count = var.mock_dependencies_enabled ? 1 : 0

  metadata {
    name      = local.mock_name
    namespace = kubernetes_namespace_v1.app.metadata[0].name

    labels = {
      "app.kubernetes.io/name"    = local.mock_name
      "app.kubernetes.io/part-of" = "withdrawal-soles"
    }
  }

  spec {
    replicas = var.mock_replicas

    selector {
      match_labels = {
        "app.kubernetes.io/name" = local.mock_name
      }
    }

    template {
      metadata {
        labels = {
          "app.kubernetes.io/name"    = local.mock_name
          "app.kubernetes.io/part-of" = "withdrawal-soles"
        }
      }

      spec {
        container {
          name              = local.mock_name
          image             = local.image_uri
          image_pull_policy = var.image_pull_policy
          command           = ["uvicorn", "tools.mock_dependencies:app", "--host", "0.0.0.0", "--port", "8001"]

          port {
            container_port = 8001
            name           = "http"
          }

          resources {
            requests = {
              cpu    = "50m"
              memory = "64Mi"
            }
            limits = {
              cpu    = "250m"
              memory = "256Mi"
            }
          }

          readiness_probe {
            http_get {
              path = "/health"
              port = 8001
            }

            initial_delay_seconds = 5
            period_seconds        = 5
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "mock" {
  count = var.mock_dependencies_enabled ? 1 : 0

  metadata {
    name      = local.mock_name
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }

  spec {
    selector = {
      "app.kubernetes.io/name" = local.mock_name
    }

    port {
      name        = "http"
      port        = 8001
      target_port = 8001
      protocol    = "TCP"
    }
  }
}
