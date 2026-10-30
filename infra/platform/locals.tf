locals {
  image_uri = "${data.terraform_remote_state.infra.outputs.ecr_repository_url}:${var.image_tag}"

  database_url = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${data.terraform_remote_state.infra.outputs.rds_endpoint}/${data.terraform_remote_state.infra.outputs.rds_database_name}"

  gateway_service = "traefik.${var.traefik_namespace}.svc.cluster.local"

  app_name  = "withdrawal-soles"
  mock_name = "mock-dependencies"
}
