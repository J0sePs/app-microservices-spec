resource "kubernetes_ingress_v1" "gateway" {
  metadata {
    name      = "withdrawal-soles"
    namespace = kubernetes_namespace_v1.app.metadata[0].name

    annotations = {
      "traefik.ingress.kubernetes.io/router.entrypoints" = "web"
    }
  }

  spec {
    ingress_class_name = "traefik"

    rule {
      http {
        # Routes come from local.ingress_paths: stub routes only when
        # mock_dependencies_enabled, and /v1/ only when wallet_mock_enabled.
        dynamic "path" {
          for_each = local.ingress_paths

          content {
            path      = path.value.path
            path_type = "Prefix"

            backend {
              service {
                name = path.value.service
                port {
                  number = path.value.port
                }
              }
            }
          }
        }
      }
    }
  }

  depends_on = [
    helm_release.traefik,
    kubernetes_service_v1.app,
    kubernetes_service_v1.mock,
  ]
}
