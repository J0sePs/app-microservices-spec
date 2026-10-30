# Tasks

## 1. Platform module scaffolding

- [x] 1.1 Create `infra/platform/versions.tf`, `providers.tf`, `data.tf`, `variables.tf`, and `locals.tf` with Kubernetes/Helm providers, remote state, and validated inputs; verify `terraform fmt -check` and `terraform validate`.
- [x] 1.2 Create `infra/platform/.gitignore` for local state and variable files; verify `git status` does not show state or secrets.

## 2. Traefik gateway

- [x] 2.1 Create the `traefik` namespace and Helm release pinned to chart `42.2.0` with two replicas and a LoadBalancer Service; verify `terraform validate` and the plan includes the Helm release.
- [x] 2.2 Add a data source for the Traefik Service and gateway hostname/URL outputs; verify the output expressions are valid.

## 3. Namespace, secret, and migrations

- [x] 3.1 Create the `withdrawal-soles` namespace and database Secret from the sensitive password; verify the plan shows the namespace and Secret and no password output.
- [x] 3.2 Create the Alembic migration Job with `wait_for_completion` and a dependency on the Secret; verify the plan shows the Job.

## 4. Application and dependency workloads

- [x] 4.1 Create the `withdrawal-soles` Deployment with two replicas, health probes, gateway URLs, and the ECR image tag; verify the plan shows the Deployment.
- [x] 4.2 Create the `mock-dependencies` Deployment and Services for both workloads; verify the plan shows both Services and the mock Deployment.

## 5. Gateway routing

- [x] 5.1 Create the Ingress for the `traefik` class with application and mock paths; verify the plan shows the Ingress and that the paths are longest-prefix ordered.
- [x] 5.2 Update `scripts/deploy-eks-demo.sh` to build/push the image and apply `infra/platform` with the tag; verify `bash -n` and a dry run of the commands.
- [x] 5.3 Update `infra/platform/README.md` and the root README with the two-stage apply, gateway URL, and destroy order; verify links resolve.

## 6. Verification and handoff

- [x] 6.1 Run `terraform fmt -check -recursive`, `terraform init -backend=false`, and `terraform validate` in `infra/platform`; verify all pass.
- [x] 6.2 Apply the infra and platform modules, confirm two Traefik replicas, two application replicas, the mock, completed migrations, and the gateway output; verify a withdrawal through the gateway.
- [x] 6.3 Destroy the platform and infra in order and confirm no billable resources remain; record the teardown evidence.
- [x] 6.4 Record evidence in `feature_list.json`, update `progress.md` and `session-handoff.md`, and run `./init.sh`; verify 5/5 subsystems and all checks pass.

## Workflow follow-up

- Archive the change after review and confirm the `eks-application-platform` spec is in `openspec/specs/`.
