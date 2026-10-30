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

          env {
            name  = "WITHDRAWAL_SOLES_USER_SERVICE_URL"
            value = "http://${local.gateway_service}"
          }

          env {
            name  = "WITHDRAWAL_SOLES_TRANSACTION_SERVICE_URL"
            value = "http://${local.gateway_service}"
          }

          env {
            name  = "WITHDRAWAL_SOLES_BUSINESS_TIMEZONE"
            value = "America/Lima"
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
