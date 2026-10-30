# AWS platform infrastructure

Terraform root module for the `withdrawal-soles` target environment. It creates
the VPC, EKS cluster and managed node group, ECR repository, and private RDS
PostgreSQL 15 instance described in
`openspec/architecture/system-context.md`.

This module does **not** deploy the application, Traefik, or Kubernetes
manifests. Those are separate follow-ups.

## Resources

| Area | Resources |
| --- | --- |
| Network | VPC, two public subnets, two private subnets, internet gateway, NAT gateway, route tables |
| Compute | EKS cluster, managed node group in the private subnets, IAM roles and policies |
| Registry | ECR repository with scan-on-push and immutable tags |
| Data | RDS PostgreSQL 15, DB subnet group, security group restricted to EKS nodes |
| Access | Security groups for control plane, nodes, and database |

## Prerequisites

- Terraform 1.9 or newer.
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

Tags are immutable, so use a unique tag such as the Git commit SHA.

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

The script builds and pushes the image, runs the Alembic migration Job, creates
the database Secret, and deploys two `withdrawal-soles` replicas plus
`mock-dependencies`. It does not create a LoadBalancer. Access the app with:

```bash
kubectl -n withdrawal-soles port-forward svc/withdrawal-soles 18080:80
```

Then open `http://localhost:18080/docs`. The script reads the database password
from the ignored `infra/terraform/terraform.tfvars`; no secret is committed.

### Public URL (optional, adds cost)

To expose the demo publicly, switch the Service to `LoadBalancer`:

```bash
kubectl -n withdrawal-soles patch svc withdrawal-soles \
  --type merge -p '{"spec":{"type":"LoadBalancer"}}'
kubectl -n withdrawal-soles get svc withdrawal-soles -w
```

AWS creates a Classic LoadBalancer and returns a DNS name. It adds roughly
$0.025/hour plus traffic. The demo has no gateway authentication and trusts the
`X-User-Id` header, so this endpoint is for practice only. Remove the Service or
run `terraform destroy` when finished.

## Destroy

```bash
terraform destroy
```

If deletion protection was enabled, set `db_deletion_protection = false` and
apply the change before destroying. The default configuration skips the final
snapshot for disposable environments.

## Follow-ups

- Add an S3 remote backend with state locking before shared use.
- Enable Multi-AZ RDS and one NAT gateway per availability zone for production.
- Deploy Traefik and the service manifests after the cluster is approved.
- Add an OIDC-backed CI plan job instead of long-lived AWS credentials.
