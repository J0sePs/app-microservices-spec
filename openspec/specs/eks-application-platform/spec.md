# eks-application-platform Specification

## Purpose
Defines the reproducible Kubernetes platform layer above the AWS cluster:
Traefik gateway, application namespace, database secret, migrations, service
deployments, and gateway routing.

## Requirements

### Requirement: Traefik gateway installation

The platform Terraform module SHALL install Traefik v3 from a pinned Helm chart
with two replicas, a `LoadBalancer` Service, and the HTTP entrypoint exposed on
port 80.

#### Scenario: Gateway is installed after the cluster

- **WHEN** the platform module is applied after the infra module
- **THEN** the `traefik` namespace contains a ready Traefik Deployment and a
  LoadBalancer Service with a public hostname

#### Scenario: Gateway hostname is available

- **WHEN** the LoadBalancer receives its hostname
- **THEN** the module exposes the hostname and a ready-to-use HTTP URL as outputs

### Requirement: Application namespace and secret

The platform module SHALL create a dedicated `withdrawal-soles` namespace and a
Secret containing the PostgreSQL connection URL. The database password MUST come
from a sensitive variable and MUST NOT be committed or emitted as an output.

#### Scenario: Secret is created without exposing the password

- **WHEN** the platform module is applied
- **THEN** the namespace and Secret exist and no Terraform output contains the
  database password

### Requirement: Migration Job runs before the application

The platform module SHALL run an Alembic migration Kubernetes Job before the
application Deployment is created, and the Job MUST complete successfully.

#### Scenario: Migration completes first

- **WHEN** the platform module is applied to an empty database
- **THEN** the migration Job completes and the application starts against the
  migrated schema

### Requirement: Application and mock deployment

The platform module SHALL deploy `withdrawal-soles` with two replicas and
`mock-dependencies` with one replica. Both MUST use the image built from the ECR
repository and the same immutable image tag, and the application MUST expose
health probes.

#### Scenario: Both workloads are ready

- **WHEN** the platform module is applied with a pushed image tag
- **THEN** two application pods and one mock pod become ready

#### Scenario: Application reaches dependencies through the gateway

- **WHEN** the application validates ownership or reports a transaction
- **THEN** it calls the in-cluster Traefik Service, which routes the request to
  the mock dependency

### Requirement: Gateway routing

The platform module SHALL create an Ingress for the Traefik IngressClass that
routes withdrawal, health, documentation, and root paths to the application and
account and transaction paths to the mock dependency.

#### Scenario: Withdrawal request reaches the application

- **WHEN** a client calls `/api/v1/withdrawals` through the gateway
- **THEN** Traefik forwards the request to the `withdrawal-soles` Service

#### Scenario: Dependency request reaches the mock

- **WHEN** the application calls `/api/v1/accounts/.../ownership` through the
  gateway
- **THEN** Traefik forwards the request to the `mock-dependencies` Service

### Requirement: Reproducible two-stage apply

The platform module SHALL read cluster values from the infra module's local
state, require the cluster to exist, and pass formatting, initialization, and
validation checks without applying Kubernetes resources.

#### Scenario: Static checks pass

- **WHEN** an operator runs `terraform fmt -check -recursive`,
  `terraform init -backend=false`, and `terraform validate` in
  `infra/platform`
- **THEN** every command exits successfully

#### Scenario: Apply order is explicit

- **WHEN** an operator applies the platform module before the infra module
- **THEN** Terraform fails with a clear missing-state error instead of creating
  partial Kubernetes resources

### Requirement: Platform outputs

The platform module SHALL output the gateway hostname, gateway URL, deployed
image URI, and application namespace.

#### Scenario: Operator reads the gateway URL

- **WHEN** the platform module finishes applying
- **THEN** the outputs include the public gateway URL for the application
