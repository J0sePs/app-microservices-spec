# Design

## Context

See `proposal.md` for motivation and
`specs/eks-application-platform/spec.md` for requirements. The infra root
module in `infra/terraform/` creates the VPC, EKS cluster, node group, ECR
repository, and RDS instance. The cluster is destroyed between practice
sessions, so the platform layer must be easy to apply and destroy independently.

Terraform cannot reliably configure the Kubernetes and Helm providers against a
cluster created in the same apply: the provider needs a known API endpoint and
CA before Kubernetes resources can be planned. A second root module avoids that
bootstrapping problem.

## Goals / Non-Goals

**Goals:**

- Keep cluster infrastructure and Kubernetes workloads in separate state files.
- Make Traefik, the application, the mock dependency, the database Secret, the
  migration Job, and the Ingress reproducible with one `terraform apply`.
- Keep the image build in CI or a small local script, not in Terraform.
- Expose the gateway URL from Terraform outputs.

**Non-Goals:**

- Building or pushing container images inside Terraform.
- Installing the AWS Load Balancer Controller.
- TLS, DNS, authentication, or production secret management.
- Deploying the other five platform services.

## Decisions

### 1. Two Terraform roots with remote state

`infra/platform/` reads `infra/terraform/terraform.tfstate` with the `local`
remote-state backend. The infra outputs provide the cluster endpoint, CA data,
cluster name, ECR URL, RDS endpoint, and database name.

This keeps provider configuration valid at plan time and lets the platform be
destroyed without touching the cluster. The alternative — one root module — was
rejected because the Kubernetes/Helm providers would need a cluster endpoint
that does not exist until the same apply creates it.

### 2. Traefik Helm chart with a LoadBalancer Service

Use the official `traefik` chart pinned to `42.2.0`, two replicas, the default
HTTP entrypoint on port 80, and a `LoadBalancer` Service. The in-tree AWS cloud
provider creates a Classic LoadBalancer, which is sufficient for a practice
environment and avoids the AWS Load Balancer Controller.

The chart also creates the `traefik` IngressClass and enables the Kubernetes
Ingress provider. The alternative — hand-written Traefik Deployments — would
duplicate chart defaults and make upgrades harder.

### 3. Standard Kubernetes Ingress instead of IngressRoute CRDs

The ingress uses `networking.k8s.io/v1` Ingress resources with the `traefik`
IngressClass. This avoids a plan-time dependency on Traefik CRDs that do not
exist until the Helm release is applied.

Paths for `/api/v1/accounts` and `/api/v1/transactions` target the mock; longer
prefixes take precedence over the root path that targets the application. The
same gateway is used for the application's outbound ownership and reporting
calls, so inter-service HTTP still goes through Traefik.

### 4. Migration Job before the Deployment

An Alembic Job runs before the application Deployment and uses the same image and
database Secret. The Job is a separate Kubernetes resource with
`wait_for_completion`; the Deployment depends on it. The alternative — a
migration init container in every replica — would race when two replicas start.

### 5. Image build remains outside Terraform

Terraform consumes `var.image_tag` and composes the image URI from the ECR
output. `scripts/deploy-eks-demo.sh` builds the image, pushes it with a unique
tag, and applies the platform module with that tag. This keeps Docker builds in
CI or the developer machine and avoids an imperative `null_resource` in the
Terraform graph.

### 6. Secret from a sensitive variable

`db_password` is a required sensitive variable in both roots. The platform
module builds the asyncpg URL and stores it in a Kubernetes Secret; no password
is output. Operators can supply it through `TF_VAR_db_password` or an ignored
`terraform.tfvars`.

### 7. Practice-only public exposure

Traefik's LoadBalancer is public and the application trusts `X-User-Id`; there
is no gateway authentication. The module is for practice, not production.
Removing the Helm release or running the destroy script removes the load
balancer.

## Risks / Trade-offs

- [Two states can drift] → Apply infra first and platform second; the deploy and
  destroy scripts enforce the order.
- [Traefik chart upgrades can change values] → Pin the chart version and review
  the plan before upgrading.
- [Classic LoadBalancer adds cost] → Destroy the platform before the cluster; the
  cleanup script removes the namespace and load balancer.
- [The image tag may not exist] → The deploy script builds and pushes before
  apply; the deployment waits on image pull.
- [Public endpoint has no authentication] → Practice-only data; add JWT
  validation at the gateway before production use.
- [Local state] → Documented follow-up to add an S3 backend with locking.

## Migration Plan

1. Create the platform module and pin the Traefik chart.
2. Apply the infra module and build/push the application image.
3. Apply the platform module.
4. Verify Traefik, pods, migrations, health, docs, and a withdrawal through the
   gateway.
5. Destroy the platform (namespace and load balancer) before destroying infra.

## Open Questions

None. Remote state and production authentication are documented follow-ups.
