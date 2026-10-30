resource "kubernetes_namespace_v1" "traefik" {
  metadata {
    name = var.traefik_namespace

    labels = {
      "app.kubernetes.io/part-of" = "withdrawal-soles"
      "app.kubernetes.io/name"    = "traefik"
    }
  }
}

resource "helm_release" "traefik" {
  name       = "traefik"
  namespace  = kubernetes_namespace_v1.traefik.metadata[0].name
  repository = "https://traefik.github.io/charts"
  chart      = "traefik"
  version    = var.traefik_chart_version
  timeout    = 600
  wait       = true
  atomic     = true

  set = [
    {
      name  = "deployment.replicas"
      value = tostring(var.traefik_replicas)
    },
    {
      name  = "service.spec.type"
      value = "LoadBalancer"
    },
    {
      name  = "api.dashboard"
      value = "false"
    },
    {
      name  = "ports.web.exposedPort"
      value = "80"
    },
    {
      name  = "providers.kubernetesIngress.enabled"
      value = "true"
    },
    {
      name  = "providers.kubernetesCRD.enabled"
      value = "true"
    },
  ]

  depends_on = [kubernetes_namespace_v1.traefik]
}

data "kubernetes_service_v1" "traefik" {
  metadata {
    name      = "traefik"
    namespace = kubernetes_namespace_v1.traefik.metadata[0].name
  }

  depends_on = [helm_release.traefik]
}
