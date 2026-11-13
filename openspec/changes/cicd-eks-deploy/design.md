# Design

## Context

See `proposal.md` for motivation. `infra/terraform` creates the VPC, EKS,
node group, ECR, and RDS. `infra/platform` installs Traefik and the
`withdrawal-soles` workloads through the Kubernetes and Helm providers. Both
roots kept local state, and the platform read the infra state from
`../terraform/terraform.tfstate`. The stack is destroyed between practice runs,
so both states are empty when this change starts.

The cluster is shared: `billetera-api` lives in namespace `billetera` and
listens on port `3000`. It serves `/v1/*` wallet routes only; `/usuarios`,
`/api/v1/accounts`, and `/api/v1/transactions` still come from
`mock-dependencies`.

## Goals / Non-Goals

**Goals:**

- A push to `main` verifies, builds, pushes, and rolls out the service with no
  laptop involved.
- Pull requests run every verification gate but never touch AWS.
- The deployment reaches the wallet through cluster DNS and signs tokens with
  the same secret and issuer as `billetera-api`.
- CI and operators share one Terraform state with locking.

**Non-Goals:**

- Applying `infra/terraform` (cluster, RDS) from CI. It stays an operator step
  because it creates billable resources.
- OIDC role federation. The request uses static access keys; OIDC is a later
  hardening step.
- Managing the `billetera` namespace or the Traefik release of another team.

## Decisions

### 1. S3 backend with native lockfiles

Both roots declare `backend "s3" {}` and receive `bucket`, `key`, `region`,
`encrypt`, and `use_lockfile` at init time through `scripts/tf-init.sh`. Keys
are `withdrawal-soles/infra.tfstate` and `withdrawal-soles/platform.tfstate`.
Terraform 1.10+ locks with an S3 lockfile, so no DynamoDB table is needed.

The platform reads the infra outputs with `terraform_remote_state` backend
`s3`, using `var.state_bucket` and `var.infra_state_key`.

`scripts/bootstrap-tf-state.sh` creates the bucket once with versioning,
AES256 encryption, and a public-access block. The bucket is not destroyed by
`destroy-eks-demo.sh`.

Alternative rejected: deploy with `kubectl set image` only. It needs no state,
but environment and manifest changes would never reach the cluster from CI and
Terraform would drift on every merge.

`scripts/tf-init.sh` never passes `-reconfigure` or `-force-copy`. If a
checkout still holds a local state, `terraform init` stops and asks for
`-migrate-state`, so state is never silently discarded.

### 2. ECR: immutable commit tags, mutable `latest`

`image_tag_mutability = "IMMUTABLE_WITH_EXCLUSION"` with a wildcard exclusion
for `latest`. Commit SHA tags stay immutable; `latest` moves to the newest
build. The lifecycle policy:

1. expires untagged images one day after push;
2. keeps the newest `ecr_max_image_count` images (default 15) of any tag.

`latest` always points at the newest image, so rule 2 never expires it.

CI skips the build when the SHA tag already exists, so re-running a workflow
for the same commit does not fail on the immutable tag.

### 3. CI cluster access

`bootstrap_cluster_creator_admin_permissions` covers only the identity that
created the cluster. `var.cluster_admin_principal_arns` (default empty) adds an
EKS access entry with `AmazonEKSClusterAdminPolicy` for each ARN, so a
dedicated CI IAM user can run the platform apply. If CI uses the same IAM user
that created the cluster, the list can stay empty.

### 4. Wallet URL and mock toggles

- `wallet_service_url` defaults to
  `http://billetera-api.billetera.svc.cluster.local:3000`. Pod-to-pod traffic in
  the shared cluster does not need the public gateway.
- `wallet_mock_enabled` (default `false`): when `true`, the Ingress adds the
  `/v1/` route to `mock-dependencies` and the service calls the wallet through
  the in-cluster Traefik Service.
- `mock_dependencies_enabled` (default `true`): deploys the stub for users,
  accounts, and transactions. When `false`, the stub Deployment, Service, and
  routes are removed and `user_service_url`, `users_service_url`, and
  `transaction_service_url` must point at real services; a precondition rejects
  `wallet_mock_enabled = true` without the stub.

The Ingress paths are built from a list in `locals.tf` and rendered with a
`dynamic "path"` block, so toggles add or remove routes without duplicated
blocks.

### 5. Shared service JWT

`var.jwt_secret` (sensitive, at least 16 characters, no default) is stored in
the `withdrawal-jwt` Secret. The Deployment maps it to
`WITHDRAWAL_SOLES_AUTH_JWT_SECRET`, `WITHDRAWAL_SOLES_WALLET_JWT_SECRET`, and
`WITHDRAWAL_SOLES_USERS_JWT_SECRET`, and sets the three matching issuer
variables from `var.jwt_issuer` (default `billetera-dev`). The value must equal
`JWT_SECRET` in `billetera-api`. A pod-template annotation carries the
Secret's `resource_version`, so rotating the secret restarts the pods without
writing any hash of the secret into pod metadata.

### 6. Pipeline shape

`.github/workflows/verify.yml` keeps its name and its `./init.sh` step (the
harness validator requires both) and gains these jobs:

| Job | Runs on | Purpose |
| --- | --- | --- |
| `checks` | push, PR | `make lint`, `make test`, `make openapi-check` |
| `verify` | push, PR | `./init.sh` (harness + OpenSpec + project checks) |
| `terraform` | push, PR | `scripts/verify-terraform.sh` |
| `image` | push to `main` with `EKS_DEPLOY_ENABLED=true` | ECR login, build, push `<sha>` and `latest` |
| `deploy` | after `image` | `terraform apply` on `infra/platform`, `aws eks update-kubeconfig`, rollout status, image check, `/health` through the gateway |

Concurrency cancels superseded pull-request runs only. The `deploy` job has its
own `eks-deploy` group that never cancels, so a running `terraform apply` is
never killed and no lock is left behind.

The apply only manages resources declared in `infra/platform`: the
`withdrawal-soles` and `traefik` namespaces. It never touches `billetera`.

## Risks / Trade-offs

- Static AWS keys in GitHub secrets → scope the IAM user to this project and
  rotate keys; move to OIDC later.
- The CI principal is cluster admin because the platform apply manages
  namespaces and a Helm release → acceptable for the practice cluster.
- If another team also installs Traefik in the shared cluster, two ingress
  controllers would compete for the `traefik` class → coordinate before
  enabling the deploy.
- Pushes to `main` while the stack is destroyed → the deploy jobs are skipped
  unless `EKS_DEPLOY_ENABLED` is `true`.

## Migration Plan

1. Run `scripts/bootstrap-tf-state.sh` once.
2. Export `TF_STATE_BUCKET`, then run `scripts/tf-init.sh terraform` and
   `scripts/tf-init.sh platform` (add `-migrate-state` once if a local state
   still exists).
3. `terraform -chdir=infra/terraform apply`, then `./scripts/deploy-eks-demo.sh`
   or a push to `main` with `EKS_DEPLOY_ENABLED=true`.

Rollback: set `EKS_DEPLOY_ENABLED=false`, then redeploy a previous SHA with
`terraform -chdir=infra/platform apply -var image_tag=<sha>`.
