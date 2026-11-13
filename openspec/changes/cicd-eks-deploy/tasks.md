# Tasks

## 1. Shared Terraform state

- [x] 1.1 Add `backend "s3" {}` to both roots, `scripts/tf-init.sh`, `scripts/bootstrap-tf-state.sh`, and `infra/backend.hcl.example`; verify `bash -n` and `terraform validate`.
- [x] 1.2 Read the infra outputs from S3 in `infra/platform/data.tf` with `state_bucket` and `infra_state_key` variables; verify `terraform validate`.

## 2. ECR and cluster access

- [x] 2.1 Switch ECR to `IMMUTABLE_WITH_EXCLUSION` for `latest` and add the lifecycle policy with `ecr_max_image_count`; verify `terraform validate` and the policy JSON.
- [x] 2.2 Add `cluster_admin_principal_arns` access entries and the `ecr_repository_name` and `aws_region` outputs; verify `terraform validate`.

## 3. Platform configuration

- [x] 3.1 Default `wallet_service_url` to `http://billetera-api.billetera.svc.cluster.local:3000`; add `wallet_mock_enabled`, `mock_dependencies_enabled`, and service URL overrides with a precondition; verify `terraform validate`.
- [x] 3.2 Build the Ingress paths from a local list with a `dynamic` block; verify the rendered paths for each toggle with `terraform console`.
- [x] 3.3 Add the `withdrawal-jwt` Secret, `jwt_secret` and `jwt_issuer` variables, JWT env vars, and the secret-version annotation; verify `terraform validate`.

## 4. OpenAPI contract check

- [x] 4.1 Add `openapi-spec-validator` to the dev extras and a `make openapi-check` target that regenerates, diffs, and validates `api/openapi.yaml`; verify it passes on the current tree and fails on an injected drift.

## 5. CI/CD workflow

- [ ] 5.1 Extend `.github/workflows/verify.yml` with `checks`, `image`, and `deploy` jobs, keeping `./init.sh`; verify YAML parses, `actionlint` passes, and `node scripts/validate-harness.mjs` passes. (YAML and harness pass; `actionlint` was blocked by the local permission policy and is still pending.)

## 6. Scripts and docs

- [x] 6.1 Update `deploy-eks-demo.sh` and `destroy-eks-demo.sh` for the S3 backend, `JWT_SECRET`, and `WALLET_MOCK_ENABLED`; verify `bash -n`.
- [x] 6.2 Update `infra/terraform/README.md`, `infra/platform/README.md`, and the `.tfvars.example` files with the backend, secrets, and new variables.

## 7. Verification and handoff

- [x] 7.1 Run `./scripts/verify-terraform.sh`, `make verify`, `make openapi-check`, `openspec validate --all --strict`, and `./init.sh`; verify all pass.
- [ ] 7.2 Bootstrap the state bucket, apply the infra module, register the GitHub secrets and variables, push to `main`, and confirm the image, rollout, and `/health` through the gateway (requires AWS; pending until the stack is re-created).
- [x] 7.3 Record evidence in `feature_list.json`, update `progress.md` and `session-handoff.md`.

## Workflow follow-up

- Archive the change after 7.2 passes and confirm the `continuous-delivery` spec is in `openspec/specs/`.
