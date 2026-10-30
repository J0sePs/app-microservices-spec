# Design

## Context

See `proposal.md` for motivation and
`specs/aws-platform-infrastructure/spec.md` for requirements. The repository
currently defines the target topology only in documentation. The service is
containerized, uses PostgreSQL 15, and expects to run behind Traefik on EKS.

The AWS account is reachable with operator credentials, but this change must
remain verifiable in CI where no credentials exist. The Terraform version
available in the workspace is 1.14.x.

## Goals / Non-Goals

**Goals:**

- Provide one root module that creates the network, EKS cluster, node group,
  ECR repository, and RDS instance in a repeatable order.
- Make the plan readable and reviewable one resource at a time.
- Keep secrets out of the repository and state outputs sensitive.
- Make static verification possible without AWS credentials.

**Non-Goals:**

- Deploying `withdrawal-soles`, Traefik, or any Kubernetes manifest.
- Creating per-service databases for the other five services.
- Remote state, state locking, or a CI apply pipeline.
- Multi-region, multi-AZ RDS, or one NAT gateway per availability zone.
- DNS, TLS certificates, VPN, or bastion access.

## Decisions

### 1. Raw resources instead of registry modules

The root module uses `aws_vpc`, `aws_subnet`, `aws_eks_cluster`,
`aws_eks_node_group`, `aws_ecr_repository`, and `aws_db_instance` directly
instead of the `terraform-aws-modules` VPC/EKS/RDS modules.

This keeps the plan explicit, avoids a module version matrix, and lets the
security-group and subnet relationships be reviewed in one repository. The
trade-off is more code to maintain. Official modules remain a reasonable
alternative once the platform needs multi-cluster or multi-account patterns.

### 2. Two availability zones with one NAT gateway

Public and private subnets are created in the first two available AZs of the
region. A single NAT gateway serves the private route table.

Two AZs satisfy the EKS and RDS subnet requirements and keep the design small.
One NAT gateway avoids doubling NAT cost for a development environment. The
trade-off is a single NAT failure domain; production should use one NAT gateway
per AZ or VPC endpoints. The route table and subnet layout makes that change
local.

### 3. Managed node group with an explicit node security group

The node group uses a launch template that attaches a dedicated node security
group. Rules allow node-to-node traffic and control-plane communication, and the
RDS security group accepts port 5432 only from that node group.

The alternative is to rely on the EKS-created cluster security group. An
explicit group makes the database ingress rule unambiguous and keeps future
node-pool additions from inheriting unintended access. Nodes run AL2023 on
`t3.medium` by default, with configurable instance types and a 1-3 node scaling
range.

### 4. Single-AZ RDS PostgreSQL 15 for the development target

RDS uses PostgreSQL 15, `db.t4g.micro`, 20 GB gp3 storage, encryption at rest,
7-day backups, and no public access. `multi_az` is a variable defaulting to
`false`.

This is sufficient to validate the application contract at low cost. Production
should enable Multi-AZ, increase backup retention, and use a larger instance
class. Deletion protection and final snapshots are variables so a demo stack can
be destroyed cleanly.

### 5. ECR with immutable tags and scan on push

The repository name includes the project and service. Tags are immutable so a
deployment cannot silently change an image, and scan on push gives basic
vulnerability visibility. CI can still publish unique SHA tags.

The alternative is mutable tags for convenience. Rejected because mutable tags
make rollbacks and audit trails unreliable.

### 6. Local state, no backend in this change

The root module uses local state and ignores `*.tfstate` and `*.tfvars` in git.
Remote state is deliberately deferred so the change does not require an S3
bucket and DynamoDB table in the same proposal.

`terraform init -backend=false` works without a backend, and the README documents
the follow-up to add an S3 backend before shared use. The provider lock file is
committed for reproducibility.

### 7. Static checks in CI, plan with operator credentials

CI runs `terraform fmt -check -recursive`, `terraform init -backend=false`, and
`terraform validate`. It does not run `plan` or `apply` because pull requests do
not receive AWS credentials.

Operators run `plan` locally with credentials. This keeps the pipeline free of
long-lived secrets while still catching syntax, formatting, and provider-schema
errors. A future OIDC role can add a protected plan job.

## Risks / Trade-offs

- [Single NAT gateway is a failure domain] → Document the production change and
  keep the private route table isolated so one NAT per AZ is a local edit.
- [Single-AZ RDS loses availability during maintenance] → `multi_az` is a
  variable; production enables it.
- [EKS versions retire] → Kubernetes version is a variable and the README
  documents the upgrade command.
- [Local state can be lost or committed] → `.gitignore` excludes state and
  variable files; README requires a remote backend before shared use.
- [AWS resources cost money] → `plan` is free; the README warns that `apply`
  creates billable EKS, EC2, NAT, and RDS resources and documents `destroy`.
- [Database password could leak through variables or outputs] → The variable is
  sensitive and has no default; no password output exists; `.tfvars` is ignored.

## Migration Plan

1. Add the Terraform root module, variables, outputs, and example tfvars.
2. Add the verification script and CI job.
3. Run formatting, initialization, validation, and a credentialed plan.
4. Optionally apply to AWS after cost review; then configure kubectl from the
   cluster output.
5. Roll back with `terraform destroy` after removing any workloads.

## Open Questions

None. Remote state and application deployment are documented follow-ups, not
blockers for this change.
