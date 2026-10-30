# Progress Log

This is the repository-local session log. It is agent-agnostic: read it at
startup and update it before handoff. The repository is the system of record;
chat history is not.

## Current Verified State

- Repository root: the directory containing this file
- Standard startup path: `./init.sh`
- Standard verification path: `./scripts/verify.sh`
- Current highest-priority unfinished feature: none — all registered features are `passing`; the other five services are follow-ups
- Current blocker: none; the AWS practice stack is running and must be destroyed to stop charges

## Session Log

### Session 001

- Date: 2026-10-30
- Goal: Adopt the OpenSpec + five-subsystem harness template for the banking microservices project.
- Completed:
  - Bootstrapped the harness from `J0sePs/openspec-opencode-template`.
  - Replaced template identity with `app-nube-2` in `README.md`, `AGENTS.md`, and `feature_list.json`.
  - Registered product features for architecture, withdrawal-soles, and Terraform infrastructure.
  - Kept `context.md` as the project source of truth.
- Verification run:
  - `./init.sh`
  - `node scripts/validate-harness.mjs`
  - `openspec validate --all --strict`
- Evidence captured:
  - Harness: 5/5 subsystems pass, 16/16 checks.
  - OpenSpec: no items to validate yet.
- Commits: initial project adoption
- Files or artifacts updated: harness files, README, AGENTS.md, feature_list.json, progress.md, session-handoff.md
- Known risk or unresolved issue: none
- Next best step: propose `implement-withdrawal-soles`.

### Session 002

- Date: 2026-10-30
- Goal: Design and document the microservices architecture baseline.
- Completed:
  - Created and archived the `design-microservices-architecture` change.
  - Added the architecture index, service catalog, system-context diagram, six ERDs, and integration contract.
  - Defined service boundaries, database ownership, gateway-only HTTP, identity forwarding, idempotency, and transaction reporting.
- Verification run:
  - `openspec validate design-microservices-architecture --strict`
  - `./init.sh`
  - `node scripts/validate-harness.mjs`
- Evidence captured:
  - Six ERDs with mermaid `erDiagram` and constraints.
  - System-context diagram with six services, six databases, and Traefik.
  - Integration contract with withdrawal, ownership, and reporting endpoints.
  - `./init.sh`: VERIFICATION PASSED, 5/5 subsystems.
- Commits: `docs: define microservices architecture baseline`
- Files or artifacts updated: `openspec/architecture/`, `feature_list.json`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: none
- Next best step: implement `withdrawal-soles`.

### Session 003

- Date: 2026-10-30
- Goal: Implement, verify, and archive the `withdrawal-soles` service.
- Completed:
  - Implemented the hexagonal FastAPI service with domain rules, use cases, SQLAlchemy persistence, Alembic, HTTP adapters, and API routes.
  - Added 54 tests across domain, application, API, adapter, and repository layers.
  - Added Dockerfile, compose stack with PostgreSQL 15, Traefik, and local dependency stubs, plus service documentation.
  - Fixed Traefik routing for `mock-dependencies` and verified the complete withdrawal flow through the gateway.
  - Updated the architecture ERD and integration contract.
  - Archived `implement-withdrawal-soles` as `2026-10-30-implement-withdrawal-soles`; the main `withdrawal-soles` spec was created.
- Verification run:
  - `make verify` (ruff + pytest)
  - `openspec validate implement-withdrawal-soles --strict`
  - `./init.sh`
  - `docker compose config --quiet`
  - `docker compose up -d --build --force-recreate mock-dependencies traefik`
  - `curl` create, replay, and read requests through `http://localhost:8080`
  - `alembic upgrade head` against compose PostgreSQL 15
- Evidence captured:
  - 54 tests passed; ruff clean.
  - `./init.sh`: VERIFICATION PASSED, 5/5 subsystems, 16/16 checks.
  - `POST /api/v1/withdrawals`: 201 Created, `COMPLETED`, transaction `aa3e255f-40b0-4054-80ee-0e637cb30060`.
  - Idempotency replay: 200 OK with the same withdrawal `14544b68-9c70-4365-bd40-6ba0824bba15`; no duplicate.
  - `GET /health`: 200 `{"status":"ok"}`.
  - PostgreSQL tables: `withdrawal_operations`, `withdrawal_status_history`, `idempotency_records`, `reporting_attempts`, `alembic_version`.
- Commits: pending (Phase 2 implementation)
- Files or artifacts updated: `src/`, `tests/`, `migrations/`, `tools/`, `docs/withdrawal-soles.md`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `Makefile`, `pyproject.toml`, architecture docs, `feature_list.json`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: local compose stubs are not production services; the real user-service and transaction-service must honor the integration contract.
- Next best step: propose and apply the Terraform change for `infra-001`.

### Session 004

- Date: 2026-10-30
- Goal: Propose and implement the Terraform infrastructure for `infra-001` without deploying to AWS.
- Completed:
  - Created and validated the `provision-aws-eks-terraform` change.
  - Added a Terraform root module for the VPC, public/private subnets, NAT gateway, EKS cluster, managed node group, IAM roles, security groups, ECR repository, and private RDS PostgreSQL 15.
  - Added variables with validation, sensitive database credentials, deployment outputs, an example tfvars file, and operator documentation.
  - Added `scripts/verify-terraform.sh` and a credential-free Terraform CI job.
  - Updated the root README and architecture deployment notes.
  - Archived `provision-aws-eks-terraform`; the main `aws-platform-infrastructure` spec now exists.
  - Rewrote `openspec/config.yaml` with the full project context, technology stack, architecture and domain rules, verification commands, and artifact rules.
  - Set the Terraform practice defaults to two `t3.small` nodes (min 1, max 2) on EKS 1.35 and documented the approximate cost; `t3.micro` is documented as too small for EKS system pods.
- Verification run:
  - `./scripts/verify-terraform.sh`
  - `terraform fmt -check -recursive`
  - `terraform init -backend=false`
  - `terraform validate`
  - `terraform plan` with `TF_VAR_db_password` set
  - `terraform plan` without the password (expected failure)
  - `terraform plan -var='node_desired_size=5'` (expected failure)
  - `openspec validate provision-aws-eks-terraform --strict`
  - `./init.sh`
  - `docker compose ps` and `curl http://localhost:8080/health`
- Evidence captured:
  - Plan: 35 to add, 0 to change, 0 to destroy; includes VPC, subnets, EKS, node group, ECR, RDS, IAM, security groups, and outputs.
  - Cost profile: approximately $157/month or $0.22/hour in `us-east-1` plus data transfer and taxes; EKS control plane and NAT gateway are the largest fixed costs.
  - Missing password and out-of-range node count both fail before creating resources.
  - Terraform provider 6.71.0, validated by Terraform 1.14.5.
  - Local stack remains healthy; `GET /health` returns 200.
  - Final local smoke: `POST /api/v1/withdrawals` with `Idempotency-Key: local-final-1` returned 201 `COMPLETED` for S/ 10.00.
  - No `terraform apply` was run and no AWS resources were created.
- Commits: pending (Phase 3 implementation)
- Files or artifacts updated: `infra/terraform/`, `scripts/verify-terraform.sh`, `.github/workflows/verify.yml`, `README.md`, `openspec/architecture/system-context.md`, `openspec/changes/provision-aws-eks-terraform/`, `feature_list.json`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: single NAT gateway and single-AZ RDS are development defaults; remote state and application deployment remain follow-ups.
- Next best step: keep the application local; deploy to AWS only when the account owner approves the cost, then add the Kubernetes deployment manifests as a separate change.

### Session 005

- Date: 2026-10-30
- Goal: Deploy the AWS infrastructure and the `withdrawal-soles` application to EKS for a short practice session.
- Completed:
  - Applied the Terraform stack in `us-east-1`: VPC, 2 nodes, EKS 1.35, ECR, and private RDS PostgreSQL 15.
  - Fixed the EKS security-group egress rules and the EKS-managed cluster security-group rules so nodes could join.
  - Set EKS support type to `STANDARD` and resolved the Free Tier RDS restriction with backup retention `0` and 20 GiB storage.
  - Rebooted the nodes after the network fix; both nodes reached `Ready`.
  - Built and pushed image `205346659030.dkr.ecr.us-east-1.amazonaws.com/app-nube-2-dev/withdrawal-soles:3aac6c0`.
  - Deployed `withdrawal-soles` with 2 replicas, `mock-dependencies`, the migration Job, and the database Secret in namespace `withdrawal-soles`.
  - Exposed the app locally through `kubectl port-forward` on port `18080`.
  - Added `scripts/deploy-eks-demo.sh` so the same image build, migration, and deployment can be repeated.
  - Exposed the app publicly with a Classic LoadBalancer and verified `/health`, `/docs`, and a real withdrawal.
- Verification run:
  - `terraform plan -detailed-exitcode`: no changes after apply
  - `kubectl get nodes`: 2 nodes Ready on Kubernetes 1.35
  - `kubectl -n withdrawal-soles get pods`: 2/2 app replicas, mock running, migration completed
  - `curl http://localhost:18080/health`: 200 `{"status":"ok"}`
  - `curl http://localhost:18080/docs`: 200
  - `POST http://localhost:18080/api/v1/withdrawals`: 201 `COMPLETED`, transaction `ce802eb6-e775-473a-8620-f46e4a873caf`
- Evidence captured:
  - `eks_cluster_endpoint`: `https://B8BE7639DC6933DD4E345A8D1EE0E5AE.gr7.us-east-1.eks.amazonaws.com`
  - `rds_endpoint`: `app-nube-2-dev-postgres.c2fc66is431b.us-east-1.rds.amazonaws.com:5432`
  - Public URL: `http://af7095da6a12e43adba0fe33f0c5087d-176028442.us-east-1.elb.amazonaws.com` (LoadBalancer, current IP `54.173.162.134`); the NAT gateway IP is outbound-only.
  - Public smoke test: `GET /health` 200, `GET /docs` 200, `POST /api/v1/withdrawals` 201 `COMPLETED` with transaction `f52daa2d-d767-4d0e-959b-b0660319ce7d`.
  - Approximate running cost: ~$0.22/hour plus data transfer.
- Commits: pending (AWS deployment and Terraform fixes)
- Files or artifacts updated: `infra/terraform/`, `src/withdrawal_soles/main.py`, `docker-compose.yml`, `tests/`, `docs/withdrawal-soles.md`, `feature_list.json`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: the stack is running and billing, now including the LoadBalancer; the public endpoint has no gateway authentication and trusts `X-User-Id`, so it is practice-only.
- Next best step: practice against `http://localhost:18080/docs`, then run `terraform destroy` and confirm the EKS, EC2, NAT, and RDS resources are gone.

### Session 006

- Date: 2026-10-30
- Goal: Export the application HTTP contract as an OpenAPI document.
- Completed:
  - Added `scripts/export_openapi.py` to generate `openapi.yaml` from the FastAPI app.
  - Added the `make openapi` target.
  - Documented required `X-User-Id` and `Idempotency-Key` headers, the error envelope, the 200 idempotent-replay response, the 202 report response, and the health schemas.
  - Added response models and documented 200/202/503 responses in the routes.
- Verification run:
  - `make openapi`
  - YAML parse and operation inventory: 6 operations with the expected required headers and response codes
  - `make verify`: 55 passed, ruff clean
  - `./init.sh`
- Evidence captured:
  - `openapi.yaml` at the repository root, OpenAPI 3.1.0.
  - Operations: create, list, get, cancel, retry report, and health.
- Commits: pending (OpenAPI contract)
- Files or artifacts updated: `openapi.yaml`, `scripts/export_openapi.py`, `Makefile`, `docs/withdrawal-soles.md`, `src/withdrawal_soles/api/routes/health.py`, `src/withdrawal_soles/api/routes/withdrawals.py`, `feature_list.json`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: none.
- Next best step: use the contract for client generation or review the public EKS deployment, then destroy the AWS practice stack when finished.

### Session 007

- Date: 2026-10-30
- Goal: Destroy the AWS practice stack and stop all charges.
- Completed:
  - Deleted the `withdrawal-soles` namespace, which removed the LoadBalancer.
  - Deleted the ECR image and reran `terraform destroy`.
  - Terraform destroyed the remaining ECR repository; the first destroy attempt had failed because the repository was not empty.
  - Deleted the EKS CloudWatch log group created outside Terraform.
  - Added `scripts/destroy-eks-demo.sh` for a clean repeatable teardown.
- Verification run:
  - `terraform state list`: empty
  - `terraform output -json`: `{}`
  - AWS checks: no EKS clusters, RDS instances, EC2 instances, NAT gateways, ELBs, ECR repositories, tagged VPCs, EBS volumes, security groups, or EKS log groups
  - `bash -n scripts/destroy-eks-demo.sh`
  - `./init.sh`
- Evidence captured:
  - NAT gateway `nat-03d65e48e2cac139e` is in `deleted` state.
  - The remaining EIP `32.199.142.201` belongs to `machupicchu-eip`, not this stack.
- Commits: pending (teardown and cleanup script)
- Files or artifacts updated: `scripts/destroy-eks-demo.sh`, `infra/terraform/README.md`, `README.md`, `feature_list.json`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: none; no AWS resources from this stack remain.
- Next best step: redeploy only when needed with `terraform apply` and `./scripts/deploy-eks-demo.sh`, then destroy with `./scripts/destroy-eks-demo.sh`.
