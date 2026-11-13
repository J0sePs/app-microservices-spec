# Spec Delta

## Purpose

Defines how changes to `withdrawal-soles` are verified in GitHub Actions and
delivered to the shared AWS EKS cluster.

## ADDED Requirements

### Requirement: Verification gates on every change

The CI workflow SHALL run `make lint`, `make test`, the OpenAPI contract check,
the harness gate (`./init.sh`), and the Terraform static checks on every push
to `main` and on every pull request. Any failing gate MUST stop the pipeline
before an image is built.

#### Scenario: Pull request is verified without touching AWS

- **WHEN** a pull request is opened or updated
- **THEN** lint, tests, the OpenAPI check, the harness, and the Terraform checks
  run, and no job authenticates to AWS

#### Scenario: Failing tests block delivery

- **WHEN** `make test` fails on a push to `main`
- **THEN** the image and deploy jobs do not run

### Requirement: OpenAPI contract drift detection

The repository SHALL provide `make openapi-check`, which regenerates
`api/openapi.yaml` from the FastAPI application, fails when the regenerated file
differs from the committed file, and validates the document against the OpenAPI
3 schema.

#### Scenario: Contract is out of date

- **WHEN** a route, header, or schema changes without regenerating
  `api/openapi.yaml`
- **THEN** `make openapi-check` exits non-zero and prints the diff

#### Scenario: Contract is current

- **WHEN** the committed contract matches the application
- **THEN** `make openapi-check` exits zero and reports a valid document

### Requirement: Image publishing to ECR

On a push to `main` with deployment enabled, the workflow SHALL authenticate to
AWS with the `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION`
secrets, resolve the ECR repository URL from the `infra/terraform` outputs,
build the image, and push it tagged with the full commit SHA and `latest`.

#### Scenario: New commit is published

- **WHEN** a verified commit lands on `main`
- **THEN** ECR contains the image under the commit SHA and `latest` points at
  the same digest

#### Scenario: Re-run for the same commit

- **WHEN** the workflow is re-run for a commit whose SHA tag already exists
- **THEN** the build is skipped and the existing image is deployed

### Requirement: Automated EKS rollout

After publishing, the workflow SHALL apply `infra/platform` with the commit SHA
as the image tag, run `aws eks update-kubeconfig`, wait for the
`withdrawal-soles` Deployment rollout, confirm the running image, and call
`/health` through the gateway. The rollout MUST only change resources managed by
`infra/platform` and MUST NOT modify other namespaces such as `billetera`.

#### Scenario: Successful rollout

- **WHEN** the deploy job finishes
- **THEN** every `withdrawal-soles` pod runs the commit SHA image and
  `/health` returns 200 through the gateway

#### Scenario: Deploy is disabled while the stack is down

- **WHEN** the repository variable `EKS_DEPLOY_ENABLED` is not `true`
- **THEN** the image and deploy jobs are skipped and the workflow still passes

#### Scenario: Concurrent pushes

- **WHEN** a second push lands while a deploy is applying
- **THEN** the second deploy waits for the first and the running apply is not
  cancelled
