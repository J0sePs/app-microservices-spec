# EKS application platform

Second-stage Terraform root module. It reads the cluster, ECR, and RDS values
from the `infra/terraform` state in S3 (`withdrawal-soles/infra.tfstate`) and
deploys the Kubernetes platform:

- Traefik v3 from Helm, two replicas, public `LoadBalancer` on port 80.
- `withdrawal-soles` namespace, database Secret, and `withdrawal-jwt` Secret.
- Alembic migration Job.
- `withdrawal-soles` Deployment with two replicas and health probes.
- `mock-dependencies` Deployment and Service (optional).
- Ingress routing for the application and, when enabled, the mock.
- Outputs for the gateway hostname and URL, image URI, namespace, Deployment
  name, and effective wallet URL.

GitHub Actions applies this module on every push to `main` (see
`.github/workflows/verify.yml`). It only manages the `traefik` and
`withdrawal-soles` namespaces; other namespaces such as `billetera` are never
touched.

## Prerequisites

1. The state bucket exists and `TF_STATE_BUCKET` is exported:

   ```bash
   ./scripts/bootstrap-tf-state.sh
   export TF_STATE_BUCKET=app-nube-2-tfstate-<account-id>
   ```

2. The infra stack is applied:

   ```bash
   ./scripts/tf-init.sh terraform
   terraform -chdir=infra/terraform apply
   ```

3. An image exists in ECR (CI pushes `<sha>` and `latest`; the helper script
   pushes the short SHA).

## Apply

```bash
./scripts/tf-init.sh platform
export TF_VAR_state_bucket="$TF_STATE_BUCKET"
export TF_VAR_db_password='the-same-password-used-by-rds'
export TF_VAR_jwt_secret='the-JWT_SECRET-of-billetera-api'
terraform -chdir=infra/platform apply -var image_tag=<pushed-tag>
```

Or run `./scripts/deploy-eks-demo.sh`, which builds, pushes, and applies.

`db_password` and `jwt_secret` are required and sensitive. The module never
outputs them.

## Wallet, dependency stub, and JWT

| Variable | Default | Effect |
| --- | --- | --- |
| `wallet_service_url` | `http://billetera-api.billetera.svc.cluster.local:3000` | Wallet called for debits and reversals (shared cluster DNS). |
| `wallet_mock_enabled` | `false` | `true` adds the `/v1/` route to `mock-dependencies` and points the wallet at the in-cluster Traefik Service. |
| `mock_dependencies_enabled` | `true` | Deploys the stub for `/usuarios`, `/api/v1/accounts`, and `/api/v1/transactions`. `billetera-api` does not serve these routes. |
| `user_service_url`, `users_service_url`, `transaction_service_url` | `""` | Overrides; empty uses the in-cluster Traefik gateway. Required when the stub is disabled. |
| `jwt_secret` | none | Stored in Secret `withdrawal-jwt`; injected into the auth, wallet, and users JWT settings. Must equal `JWT_SECRET` in `billetera-api`. |
| `jwt_issuer` | `billetera-dev` | Issuer for the three JWT settings. Must equal `JWT_ISSUER` in `billetera-api`. |

While `billetera-api` is not deployed in the cluster, use the wallet stub:

```bash
WALLET_MOCK_ENABLED=1 ./scripts/deploy-eks-demo.sh
```

In CI, set the repository variable `WALLET_MOCK_ENABLED=true` instead.

## Outputs

```bash
terraform -chdir=infra/platform output gateway_url
terraform -chdir=infra/platform output wallet_service_url
terraform -chdir=infra/platform output image_uri
```

The gateway URL is the Traefik LoadBalancer. The application is reachable at
`/docs`, `/health`, and `/api/v1/withdrawals`.

## Apply order

```text
bootstrap state bucket  →  infra/terraform  →  build/push image  →  infra/platform
```

The platform module fails if the infra state is missing. This avoids
configuring the Kubernetes provider against a cluster that does not exist.

## Destroy

Destroy the platform before the cluster:

```bash
./scripts/destroy-eks-demo.sh
```

The script removes the namespace and LoadBalancer, deletes ECR images,
destroys both roots in order, and deletes the EKS log group. It keeps the
state bucket.

## Security and cost

- The gateway is public and the demo has no gateway authentication; the service
  trusts `X-User-Id`, so use it for practice only.
- Traefik's `LoadBalancer` creates an AWS Classic LoadBalancer and adds cost.
- The chart and image tag are pinned so repeated applies are predictable.
- State lives in S3 with versioning, encryption, and lockfiles.
