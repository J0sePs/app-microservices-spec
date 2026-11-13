# AWS platform infrastructure

Terraform root module for the `withdrawal-soles` target environment. It creates
the VPC, EKS cluster and managed node group, ECR repository, and private RDS
PostgreSQL 15 instance described in
`openspec/architecture/system-context.md`.

This module does **not** deploy the application, Traefik, or Kubernetes
manifests; `infra/platform` does.

## Resources

| Area | Resources |
| --- | --- |
| Network | VPC, two public subnets, two private subnets, internet gateway, NAT gateway, route tables |
| Compute | EKS cluster, managed node group in the private subnets, IAM roles and policies |
| Registry | ECR repository with scan-on-push, immutable commit tags (`latest` excluded), and a lifecycle policy (untagged images expire after 1 day; newest `ecr_max_image_count` kept) |
| Data | RDS PostgreSQL 15, DB subnet group, security group restricted to EKS nodes |
| Access | Security groups for control plane, nodes, and database; optional EKS access entries for `cluster_admin_principal_arns` (CI deployer) |

## Prerequisites

- Terraform 1.10 or newer (S3 native state locking).
- AWS credentials for the target account, for example through `AWS_PROFILE`.
- `kubectl` only if you intend to connect to a deployed cluster.

## Configure

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Set the database password through the environment so it never lands in a file:

```bash
export TF_VAR_db_password='use-a-strong-password'
```

`terraform.tfvars` and all state files are ignored by git. The example file
contains no secret.

## Remote state (S3)

Both `infra/terraform` and `infra/platform` use a partial `backend "s3" {}`
so operators and GitHub Actions share one locked state. Create the bucket once
(versioned, encrypted, public access blocked), then initialize:

```bash
./scripts/bootstrap-tf-state.sh            # prints the bucket name
export TF_STATE_BUCKET=app-nube-2-tfstate-<account-id>
export AWS_REGION=us-east-1
./scripts/tf-init.sh terraform             # key withdrawal-soles/infra.tfstate
./scripts/tf-init.sh platform              # key withdrawal-soles/platform.tfstate
```

If a checkout still holds a local `terraform.tfstate` with resources, migrate
it once into the empty bucket keys (Terraform copies the local state into S3
and empties the local file; back it up first):

```bash
./scripts/tf-init.sh terraform -migrate-state -force-copy
./scripts/tf-init.sh platform -migrate-state -force-copy
```

`-force-copy` is required because `tf-init.sh` runs with `-input=false`. Never
use it when the S3 key already holds a state: it would overwrite it.

`tf-init.sh` never passes `-reconfigure` or `-force-copy`, so a local state is
never discarded silently. The destroy script keeps the bucket.

## Static verification (no AWS credentials)

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

Or from the repository root:

```bash
./scripts/verify-terraform.sh
```

## Plan (no resources created)

```bash
terraform init
terraform plan -out=tfplan
```

The plan should report the VPC, subnets, NAT gateway, EKS cluster, managed node
group, ECR repository, RDS instance, security groups, IAM roles, and outputs.
`plan` does not create billable resources.

## Cost profile

The defaults are sized for a short practice deployment, not production.
Approximate `us-east-1` on-demand prices, excluding data transfer and taxes:

| Resource | Default | Approx. monthly |
| --- | --- | --- |
| EKS control plane | 1 cluster | ~$73 |
| NAT gateway | 1 | ~$33 plus data |
| Public IPv4 for NAT | 1 | ~$3.60 |
| EC2 workers | 2 × `t3.small` | ~$30 |
| RDS PostgreSQL | 1 × `db.t4g.micro` | ~$12 |
| RDS gp3 storage | 20 GiB | ~$2.30 |
| Node EBS volumes | 2 × 20 GiB | ~$3.20 |
| ECR storage | image size | usage-based |

**Rough total: ~$157/month plus data transfer and taxes.** For short
sessions, that is about **$0.22/hour** or **~$5.20/day**. The EKS control plane
and NAT gateway dominate the bill and are charged even while idle.

`t3.small` is the smallest practical EKS worker. `t3.micro` has only 1 GiB of
RAM and is likely to run out of memory with the VPC CNI, CoreDNS, kube-proxy,
and the application. If you need a cheaper temporary demo, override
`node_instance_types = ["t3.micro"]` only after testing, and destroy the stack
when you are done.

```bash
terraform destroy
```

## Apply

> **Cost warning:** `apply` creates billable EKS, EC2, NAT gateway, and RDS
> resources. Do not run it without explicit approval from the account owner.

```bash
terraform apply tfplan
```

This change intentionally stops at a verified plan. No AWS resources were
created during implementation.

## Outputs

```bash
terraform output
terraform output -raw configure_kubectl
terraform output -raw ecr_repository_url
terraform output -raw ecr_repository_name
terraform output -raw rds_endpoint
```

`eks_cluster_certificate_authority_data` is marked sensitive. The database
password is never an output.

## Connect kubectl

After an approved apply:

```bash
aws eks update-kubeconfig --region us-east-1 --name app-nube-2-dev-eks
kubectl get nodes
```

## Publish an image

```bash
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin "$(terraform output -raw ecr_repository_url)"

docker build -t withdrawal-soles .
docker tag withdrawal-soles:latest "$(terraform output -raw ecr_repository_url):<git-sha>"
docker push "$(terraform output -raw ecr_repository_url):<git-sha>"
```

Commit tags are immutable, so use a unique tag such as the Git commit SHA.
Only `latest` can be overwritten. GitHub Actions pushes both on every merge to
`main`.

## Database connection

> **Free Tier note:** the default `db_backup_retention_period` is `0` because
> Free Tier accounts reject longer retention. Enable backups only after
> upgrading the account plan.

The RDS instance is private. Use the endpoint output from a workload inside the
VPC or through a controlled tunnel. The service expects:

```text
postgresql+asyncpg://withdrawal:<password>@<rds_endpoint>/withdrawal_soles_db
```

## Deploy the demo application

After an approved apply, deploy the service and its local dependency stub:

```bash
./scripts/deploy-eks-demo.sh
```

The script builds and pushes the image, then applies the second-stage
`infra/platform/` module. That module installs Traefik with a public
`LoadBalancer`, creates the namespace and database Secret, runs the Alembic
migration Job, deploys two `withdrawal-soles` replicas plus
`mock-dependencies`, and creates the gateway Ingress. The gateway URL is
printed from the platform outputs.

The platform module is documented in
[`infra/platform/README.md`](../platform/README.md). The script reads the
database password from the ignored `infra/terraform/terraform.tfvars`, and
needs `TF_STATE_BUCKET` and `JWT_SECRET` (the secret shared with
`billetera-api`) in the environment; no secret is committed.

The service calls the wallet at
`http://billetera-api.billetera.svc.cluster.local:3000` by default. While
`billetera-api` is not deployed in the cluster, use the in-cluster
`mock-dependencies` wallet stub so the debit/reversal flow still works:

```bash
WALLET_MOCK_ENABLED=1 ./scripts/deploy-eks-demo.sh
```

## Continuous delivery

`.github/workflows/verify.yml` deploys every push to `main` when the
repository variable `EKS_DEPLOY_ENABLED` is `true`. CI never applies this
module; it reads `ecr_repository_url`, `ecr_repository_name`, and
`eks_cluster_name` from the S3 state, pushes the image, and applies
`infra/platform`. If the CI IAM user is not the identity that created the
cluster, add its ARN to `cluster_admin_principal_arns` and apply.

## Destroy

For a clean teardown, use the helper script:

```bash
./scripts/destroy-eks-demo.sh
```

It removes the Kubernetes namespace and its LoadBalancer, deletes the ECR
images, runs `terraform destroy`, and deletes the EKS CloudWatch log group.
Without the script, delete the ECR images first; `force_delete` is disabled, so
`terraform destroy` refuses to delete a non-empty repository.

```bash
terraform destroy
```

If deletion protection was enabled, set `db_deletion_protection = false` and
apply the change before destroying. The default configuration skips the final
snapshot for disposable environments.

## Follow-ups

- Enable Multi-AZ RDS and one NAT gateway per availability zone for production.
- Add an OIDC-backed CI plan job instead of long-lived AWS credentials.
