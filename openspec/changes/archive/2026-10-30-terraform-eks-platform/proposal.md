# Proposal

## Why

The cluster, database, and registry are Terraform-managed, but the gateway and
application are still deployed by ad-hoc `kubectl` commands. A clean checkout
cannot reproduce Traefik, the namespace, the database Secret, the migration Job,
the application, the dependency stub, or the Ingress. This makes the practice
environment fragile and easy to leave half-deployed.

## What Changes

- Add a second Terraform root module at `infra/platform/` that reads the cluster
  state from `infra/terraform/` through `terraform_remote_state`.
- Install Traefik v3 from its Helm chart with two replicas and a public
  `LoadBalancer` Service.
- Create the `withdrawal-soles` namespace and a database Secret sourced from a
  sensitive password variable.
- Run an Alembic migration Kubernetes Job before the application rolls out.
- Deploy `withdrawal-soles` with two replicas, health probes, and gateway URLs;
  deploy `mock-dependencies` with one replica as the local dependency stub.
- Route `/api/v1/withdrawals`, `/health`, `/docs`, `/openapi.json`, and `/`
  through Traefik to the application, and `/api/v1/accounts` plus
  `/api/v1/transactions` to the mock.
- Expose the gateway hostname, gateway URL, image URI, and namespace as outputs.
- Update the deployment script to build/push the image and apply the platform
  module instead of running ad-hoc manifests.

Out of scope: building container images inside Terraform, AWS Load Balancer
Controller, TLS, authentication at the gateway, production secrets management,
and the other five services.

## Capabilities

### New Capabilities

- `eks-application-platform`: gateway installation, Kubernetes namespace and
  secret management, migration Job, application and mock deployments, Ingress
  routing, and gateway outputs.

### Modified Capabilities

- None. The infrastructure capability keeps the same requirements; this change
  consumes its outputs.

## Impact

- New `infra/platform/` module with Kubernetes and Helm providers.
- Changes to `scripts/deploy-eks-demo.sh`, `README.md`, and Terraform docs.
- The platform module requires the cluster to exist and the image to be pushed
  before apply.
- Adds a Classic LoadBalancer and two Traefik replicas while applied.
- Harness subsystems affected: state (`feature_list.json`, `progress.md`),
  verification (platform checks and live smoke test), scope (one active change),
  and lifecycle (archive after verification).
