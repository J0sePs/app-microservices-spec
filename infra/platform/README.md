# EKS application platform

Second-stage Terraform root module. It reads the cluster, ECR, and RDS values
from `../terraform/terraform.tfstate` and deploys the Kubernetes platform:

- Traefik v3 from Helm, two replicas, public `LoadBalancer` on port 80.
- `withdrawal-soles` namespace and database Secret.
- Alembic migration Job.
- `withdrawal-soles` Deployment with two replicas and health probes.
- `mock-dependencies` Deployment and Service.
- Ingress routing for the application and the mock dependency.
- Outputs for the gateway hostname, gateway URL, image URI, and namespace.

## Prerequisites

1. The infra stack is applied:

   ```bash
   terraform -chdir=infra/terraform apply
   ```

2. An image exists in ECR. The helper script builds and pushes one:

   ```bash
   ./scripts/deploy-eks-demo.sh
   ```

   Or build and push manually and set `image_tag` to the pushed tag.

## Apply

```bash
cd infra/platform
cp terraform.tfvars.example terraform.tfvars
export TF_VAR_db_password='the-same-password-used-by-rds'
terraform init
terraform apply
```

`db_password` is required and sensitive. The module never outputs it.

## Outputs

```bash
terraform output gateway_url
terraform output gateway_hostname
terraform output image_uri
terraform output application_namespace
```

The gateway URL is the Traefik LoadBalancer. The application is reachable at
`/docs`, `/health`, and `/api/v1/withdrawals`; the mock is reachable only through
the gateway paths `/api/v1/accounts`, `/api/v1/transactions`, `/usuarios`, and
`/v1/` (wallet). The deployment points the user and transaction service URLs at
the in-cluster Traefik service, and the wallet URL at `var.wallet_service_url`
(default `http://52.67.162.209`, the published Billetera Digital PEN API).

## Apply order

```text
infra/terraform  →  build/push image  →  infra/platform
```

The platform module intentionally fails if the infra state is missing. This
avoids configuring the Kubernetes provider against a cluster that does not
exist.

## Destroy

Destroy the platform before the cluster:

```bash
cd infra/platform
terraform destroy
```

Or use the repository helper, which removes the namespace/LoadBalancer, deletes
ECR images, destroys both roots in order, and deletes the EKS log group:

```bash
./scripts/destroy-eks-demo.sh
```

## Security and cost

- The gateway is public and the demo has no gateway authentication; the service
  trusts `X-User-Id`, so use it for practice only.
- Traefik's `LoadBalancer` creates an AWS Classic LoadBalancer and adds cost.
- The chart and image tag are pinned so repeated applies are predictable.
- Terraform state is local; add an S3 backend with locking before shared use.
