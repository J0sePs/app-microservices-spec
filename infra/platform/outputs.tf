output "gateway_hostname" {
  description = "Public hostname of the Traefik LoadBalancer."
  value       = try(data.kubernetes_service_v1.traefik.status[0].load_balancer[0].ingress[0].hostname, "")
}

output "gateway_ip" {
  description = "Public IP of the Traefik LoadBalancer, when AWS returns one."
  value       = try(data.kubernetes_service_v1.traefik.status[0].load_balancer[0].ingress[0].ip, "")
}

output "gateway_url" {
  description = "Public HTTP URL for the application through Traefik."
  value       = "http://${try(data.kubernetes_service_v1.traefik.status[0].load_balancer[0].ingress[0].hostname, "")}"
}

output "application_namespace" {
  description = "Namespace containing the application workloads."
  value       = kubernetes_namespace_v1.app.metadata[0].name
}

output "image_uri" {
  description = "Application image deployed by this module."
  value       = local.image_uri
}

output "traefik_release" {
  description = "Installed Traefik Helm release and chart version."
  value       = "${helm_release.traefik.name} ${helm_release.traefik.version}"
}
