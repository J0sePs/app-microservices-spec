# Spec Delta

## Purpose

Points the EKS deployment at the in-cluster wallet, makes the dependency stub
optional, aligns the service JWT with `billetera-api`, and reads infra state
from S3.

## MODIFIED Requirements

### Requirement: Application and mock deployment

The platform module SHALL deploy `withdrawal-soles` with two replicas and, when
`mock_dependencies_enabled` is true, `mock-dependencies` with one replica. Both
MUST use the image built from the ECR repository and the same immutable image
tag, and the application MUST expose health probes. The application MUST call
the PEN wallet at `wallet_service_url`, which defaults to
`http://billetera-api.billetera.svc.cluster.local:3000`.

#### Scenario: Both workloads are ready

- **WHEN** the platform module is applied with a pushed image tag and the stub
  enabled
- **THEN** two application pods and one mock pod become ready

#### Scenario: Application reaches the shared wallet by cluster DNS

- **WHEN** the application debits or reverses a wallet movement in the shared
  cluster
- **THEN** it calls `billetera-api.billetera.svc.cluster.local:3000`

#### Scenario: Application reaches dependencies through the gateway

- **WHEN** the application validates ownership or reports a transaction and the
  stub is enabled
- **THEN** it calls the in-cluster Traefik Service, which routes the request to
  the mock dependency

#### Scenario: Stub is disabled

- **WHEN** `mock_dependencies_enabled` is false
- **THEN** no mock Deployment, Service, or route exists, and the application
  uses the configured user and transaction service URLs

### Requirement: Gateway routing

The platform module SHALL create an Ingress for the Traefik IngressClass that
routes withdrawal, health, documentation, and root paths to the application.
When the stub is enabled, it SHALL route account, transaction, and user paths to
the mock dependency. It SHALL route the wallet path `/v1/` to the mock only when
`wallet_mock_enabled` is true.

#### Scenario: Withdrawal request reaches the application

- **WHEN** a client calls `/api/v1/withdrawals` through the gateway
- **THEN** Traefik forwards the request to the `withdrawal-soles` Service

#### Scenario: Dependency request reaches the mock

- **WHEN** the application calls `/api/v1/accounts/.../ownership` through the
  gateway with the stub enabled
- **THEN** Traefik forwards the request to the `mock-dependencies` Service

#### Scenario: Wallet stub is opt-in

- **WHEN** `wallet_mock_enabled` is true
- **THEN** the Ingress routes `/v1/` to the mock and the application calls the
  wallet through the in-cluster Traefik Service

#### Scenario: Wallet stub is off in the shared cluster

- **WHEN** `wallet_mock_enabled` is false
- **THEN** the Ingress has no `/v1/` route and the application calls
  `wallet_service_url`

### Requirement: Reproducible two-stage apply

The platform module SHALL read cluster values from the infra module's state in
the S3 backend, require the cluster to exist, and pass formatting,
initialization, and validation checks without applying Kubernetes resources.

#### Scenario: Static checks pass

- **WHEN** an operator runs `terraform fmt -check -recursive`,
  `terraform init -backend=false`, and `terraform validate` in
  `infra/platform`
- **THEN** every command exits successfully

#### Scenario: Apply order is explicit

- **WHEN** an operator applies the platform module before the infra module
- **THEN** Terraform fails with a clear missing-state error instead of creating
  partial Kubernetes resources

## ADDED Requirements

### Requirement: Shared service JWT

The platform module SHALL store the service JWT secret from a sensitive variable
in a Kubernetes Secret and inject it into the inbound, wallet, and users JWT
settings of the application, with the issuer from `jwt_issuer` (default
`billetera-dev`). The secret MUST NOT have a default value and MUST NOT appear
in any output.

#### Scenario: Tokens match billetera-api

- **WHEN** the application is deployed with the same `jwt_secret` as
  `billetera-api`'s `JWT_SECRET`
- **THEN** the wallet accepts the tokens the application signs, with issuer
  `billetera-dev`

#### Scenario: Missing secret blocks the plan

- **WHEN** the platform module is planned without `jwt_secret`
- **THEN** Terraform asks for the value and does not create resources

#### Scenario: Secret rotation restarts the pods

- **WHEN** `jwt_secret` changes
- **THEN** the Secret is updated and the Deployment rolls out new pods
