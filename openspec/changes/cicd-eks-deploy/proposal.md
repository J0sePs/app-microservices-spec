# Proposal

## Why

Every deployment to EKS is a manual run of `scripts/deploy-eks-demo.sh` from an
operator laptop. GitHub Actions only runs the harness and Terraform static
checks, so a merge to `main` never reaches the cluster, and nothing proves that
`api/openapi.yaml` still matches the FastAPI app.

The cluster is now shared with the `billetera-api` service, which runs in the
`billetera` namespace on port `3000`. The EKS deployment still calls the wallet
through its public IP, carries no JWT configuration (the pods fall back to the
code default secret), and always exposes the wallet stub route on the gateway.

Two blockers prevent CI from deploying today:

- Both Terraform roots use local state that is ignored by git, so a CI runner
  cannot read the ECR URL or apply `infra/platform`.
- The ECR repository rejects every tag reuse, so a `latest` tag can be pushed
  only once and old images are never removed.

## What Changes

- Move `infra/terraform` and `infra/platform` to an S3 backend with native
  lockfiles, add a bootstrap script for the state bucket, and read the infra
  outputs from S3 in the platform module.
- ECR: keep commit tags immutable but exclude `latest`, add a lifecycle policy
  that expires untagged images after one day and keeps the newest N images, and
  output the repository name.
- Optional EKS access entries so a CI IAM principal can administer the cluster.
- Platform: point `WITHDRAWAL_SOLES_WALLET_SERVICE_URL` at
  `http://billetera-api.billetera.svc.cluster.local:3000` by default; add
  `wallet_mock_enabled` (wallet stub route) and `mock_dependencies_enabled`
  (whole stub) toggles with URL overrides for users and transactions; inject the
  shared service JWT secret from a Kubernetes Secret and the issuer
  `billetera-dev` into every JWT setting.
- `make openapi-check`: regenerate `api/openapi.yaml`, fail on drift, and
  validate the document against the OpenAPI schema.
- `.github/workflows/verify.yml` becomes the CI/CD pipeline: lint, tests,
  OpenAPI drift and schema checks, harness, and Terraform checks on every push
  and pull request; on `main` only, build the image tagged with the commit SHA
  and `latest`, push it to ECR, apply `infra/platform`, and wait for the
  rollout.
- Update the local deploy/destroy scripts and docs for the S3 backend and the
  new variables.

Out of scope: applying `infra/terraform` from CI, OIDC federation for AWS,
deploying or configuring `billetera-api`, TLS, gateway authentication, and the
other five services.

## Capabilities

### New Capabilities

- `continuous-delivery`: CI verification gates, OpenAPI drift detection, image
  publishing, and automated EKS rollout from `main`.

### Modified Capabilities

- `aws-platform-infrastructure`: ECR tag exclusion and lifecycle policy, S3
  state backend, CI cluster access entries, and new outputs.
- `eks-application-platform`: in-cluster wallet URL, mock toggles, JWT Secret,
  and S3 remote state.

## Impact

- `.github/workflows/verify.yml`, `Makefile`, `pyproject.toml` (dev
  dependency `openapi-spec-validator`).
- `infra/terraform/{versions,ecr,iam,variables,outputs}.tf`, new
  `access.tf`, `backend.hcl.example`.
- `infra/platform/{versions,data,variables,locals,app,ingress,outputs}.tf`.
- `scripts/tf-init.sh` and `scripts/bootstrap-tf-state.sh` (new), updates to
  `scripts/deploy-eks-demo.sh` and `scripts/destroy-eks-demo.sh`.
- One-time S3 bucket creation; GitHub secrets and variables are required before
  the deploy jobs run.
- The deploy jobs are gated by the repository variable `EKS_DEPLOY_ENABLED`, so
  pushes to `main` keep passing while the AWS stack is destroyed.
- Harness subsystems affected: state (`feature_list.json`, `progress.md`),
  verification (`verify.yml` keeps running `./init.sh`), scope (one active
  change), lifecycle (archive after a live deploy).
