locals {
  image_uri = "${data.terraform_remote_state.infra.outputs.ecr_repository_url}:${var.image_tag}"

  database_url = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${data.terraform_remote_state.infra.outputs.rds_endpoint}/${data.terraform_remote_state.infra.outputs.rds_database_name}"

  gateway_service = "traefik.${var.traefik_namespace}.svc.cluster.local"

  app_name  = "withdrawal-soles"
  mock_name = "mock-dependencies"

  gateway_url = "http://${local.gateway_service}"

  user_service_url        = var.user_service_url != "" ? var.user_service_url : local.gateway_url
  transaction_service_url = var.transaction_service_url != "" ? var.transaction_service_url : local.gateway_url
  wallet_service_url      = var.wallet_mock_enabled ? local.gateway_url : var.wallet_service_url

  # Gateway routes, longest prefix first. Stub routes exist only when the stub
  # is deployed; the wallet stub route is opt-in through wallet_mock_enabled.
  mock_paths = concat(
    var.mock_dependencies_enabled ? ["/api/v1/accounts", "/api/v1/transactions", "/usuarios"] : [],
    var.mock_dependencies_enabled && var.wallet_mock_enabled ? ["/v1/"] : [],
  )

  app_paths = ["/api/v1/withdrawals", "/health", "/docs", "/openapi.json", "/"]

  ingress_paths = concat(
    [for path in local.mock_paths : { path = path, service = local.mock_name, port = 8001 }],
    [for path in local.app_paths : { path = path, service = local.app_name, port = 80 }],
  )

  # Environment for the application container. Values come from variables;
  # secrets are injected separately through secret_key_ref.
  app_env = merge(
    {
      WITHDRAWAL_SOLES_USER_SERVICE_URL        = local.user_service_url
      WITHDRAWAL_SOLES_TRANSACTION_SERVICE_URL = local.transaction_service_url
      WITHDRAWAL_SOLES_WALLET_SERVICE_URL      = local.wallet_service_url
      WITHDRAWAL_SOLES_BUSINESS_TIMEZONE       = "America/Lima"
      WITHDRAWAL_SOLES_AUTH_JWT_ISSUER         = var.jwt_issuer
      WITHDRAWAL_SOLES_WALLET_JWT_ISSUER       = var.jwt_issuer
      WITHDRAWAL_SOLES_USERS_JWT_ISSUER        = var.jwt_issuer
    },
    var.users_service_url != "" ? { WITHDRAWAL_SOLES_USERS_SERVICE_URL = var.users_service_url } : {},
  )

  jwt_secret_env = [
    "WITHDRAWAL_SOLES_AUTH_JWT_SECRET",
    "WITHDRAWAL_SOLES_WALLET_JWT_SECRET",
    "WITHDRAWAL_SOLES_USERS_JWT_SECRET",
  ]
}
