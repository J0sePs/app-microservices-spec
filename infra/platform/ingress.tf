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
        path {
          path      = "/api/v1/accounts"
          path_type = "Prefix"

          backend {
            service {
              name = kubernetes_service_v1.mock.metadata[0].name
              port {
                number = 8001
              }
            }
          }
        }

        path {
          path      = "/api/v1/transactions"
          path_type = "Prefix"

          backend {
            service {
              name = kubernetes_service_v1.mock.metadata[0].name
              port {
                number = 8001
              }
            }
          }
        }

        path {
          path      = "/api/v1/withdrawals"
          path_type = "Prefix"

          backend {
            service {
              name = kubernetes_service_v1.app.metadata[0].name
              port {
                number = 80
              }
            }
          }
        }

        path {
          path      = "/health"
          path_type = "Prefix"

          backend {
            service {
              name = kubernetes_service_v1.app.metadata[0].name
              port {
                number = 80
              }
            }
          }
        }

        path {
          path      = "/docs"
          path_type = "Prefix"

          backend {
            service {
              name = kubernetes_service_v1.app.metadata[0].name
              port {
                number = 80
              }
            }
          }
        }

        path {
          path      = "/openapi.json"
          path_type = "Prefix"

          backend {
            service {
              name = kubernetes_service_v1.app.metadata[0].name
              port {
                number = 80
              }
            }
          }
        }

        path {
          path      = "/"
          path_type = "Prefix"

          backend {
            service {
              name = kubernetes_service_v1.app.metadata[0].name
              port {
                number = 80
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
