# Progress Log

This is the repository-local session log. It is agent-agnostic: read it at
startup and update it before handoff. The repository is the system of record;
chat history is not.

## Current Verified State

- Repository root: the directory containing this file
- Standard startup path: `./init.sh`
- Standard verification path: `./scripts/verify.sh`
- Current highest-priority unfinished feature: none — all registered features are `passing`; the other five services are follow-ups
- Current blocker: none; the AWS practice stack is **deployed and live** as of 2026-11-13 (billing active), see `session-handoff.md`

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

### Session 008

- Date: 2026-10-30
- Goal: Move the gateway and application deployment from ad-hoc kubectl commands into Terraform.
- Completed:
  - Created `infra/platform/` with Kubernetes and Helm providers, remote state, pinned Traefik chart 42.2.0, namespace, Secret, migration Job, app and mock Deployments, Services, Ingress, and gateway outputs.
  - Updated `scripts/deploy-eks-demo.sh` to build/push the image and apply the platform module.
  - Updated `scripts/destroy-eks-demo.sh` to destroy the platform before the infra and to pass the database password.
  - Updated `scripts/verify-terraform.sh` to validate both Terraform roots.
  - Applied the infra and platform modules and verified the gateway.
- Verification run:
  - `terraform fmt -check -recursive`, `terraform init -backend=false`, and `terraform validate` in both roots
  - `terraform apply` infra: 41 resources; both nodes Ready
  - `terraform apply` platform: Traefik 2/2, application 2/2, mock 1/1, migration Job Complete
  - `GET /health`, `/docs`, `/` through the gateway: 200
  - `POST /api/v1/withdrawals` through the gateway: 201 `COMPLETED`
  - `terraform plan -detailed-exitcode` platform: no changes
- Evidence captured:
  - `gateway_hostname = ac76de6242f8b476ba99ff49e976360e-1857400072.us-east-1.elb.amazonaws.com`
  - `gateway_url = http://ac76de6242f8b476ba99ff49e976360e-1857400072.us-east-1.elb.amazonaws.com`
  - Withdrawal `23ac218d-6e1b-41cb-b3a4-bbd60ee0b80c` completed; transaction `2a5a82ad-71ca-45e5-a13c-8e4c08db4a3c`.
  - Initial migration failed because the Secret was double-base64 encoded; changing `data.url` to the raw URL and adding `replace_triggered_by` fixed it.
- Commits: pending (platform Terraform)
- Files or artifacts updated: `infra/platform/`, `scripts/deploy-eks-demo.sh`, `scripts/destroy-eks-demo.sh`, `scripts/verify-terraform.sh`, `README.md`, `infra/terraform/README.md`, `openspec/architecture/system-context.md`, `openspec/changes/terraform-eks-platform/`, `feature_list.json`, `progress.md`, `session-handoff.md`
- Teardown:
  - `scripts/destroy-eks-demo.sh` destroyed the platform first, then the infra.
  - Terraform states are empty for both roots and outputs are `{}`.
  - AWS checks found no EKS, RDS, EC2, available NAT, ELB/ALB, ECR, tagged VPC, EBS, RDS snapshot, or EKS log group.
  - The remaining EIP `32.199.142.201` is `machupicchu-eip`, unrelated to this stack.
- Known risk or unresolved issue: the public gateway had no authentication; it was practice-only and is now destroyed.
- Archived `terraform-eks-platform` as `2026-10-30-terraform-eks-platform`; the main `eks-application-platform` spec now exists.
- Next best step: keep the local compose stack for development; redeploy with the two-stage Terraform flow when needed.

### Session 009

- Date: 2026-11-03
- Goal: Execute the two-stage Terraform deployment again and leave the application available.
- Completed:
  - Applied `infra/terraform`: 41 resources, EKS 1.35, two `t3.small` nodes, RDS PostgreSQL 15, and ECR.
  - Applied `infra/platform` through `scripts/deploy-eks-demo.sh`: Traefik, namespace, Secret, migration Job, application, mock, Services, and Ingress.
  - Fixed the deploy script to update `kubeconfig` for the new cluster automatically.
  - Updated `service-reference.md` with the current practice gateway URL.
- Verification run:
  - `terraform apply` infra: 41 resources
  - `terraform apply` platform: 10 resources
  - `kubectl -n traefik get pods,svc`: 2/2 Traefik pods and LoadBalancer active
  - `kubectl -n withdrawal-soles get pods,svc,ingress`: 2/2 app, 1/1 mock, migration Complete
  - `GET /health`, `/docs`, and `/` through the gateway: 200
  - `POST /api/v1/withdrawals` through the gateway: 201 `COMPLETED`
- Evidence captured:
  - Gateway: `http://aa56b06084cae4b828ba4a1f30f3ceb6-2084714021.us-east-1.elb.amazonaws.com`
  - Withdrawal `06172ecd-6cfa-4195-b1ec-d3c302473e6f`; transaction `614bd3f4-718d-4860-8b23-49b3e9b6e783`.
- Commits: pending (redeploy evidence and script fix)
- Files or artifacts updated: `scripts/deploy-eks-demo.sh`, `service-reference.md`, `feature_list.json`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: the public gateway has no authentication and is practice-only; the stack is running and billing.
- Next best step: use the gateway for practice, then run `./scripts/destroy-eks-demo.sh` to stop charges.

### Session 010

- Date: 2026-11-03
- Goal: Verify the deployed public endpoints are correct and consumable.
- Verification run:
  - `GET /health` → 200
  - `GET /docs` → 200
  - `GET /openapi.json` → 200 with the five documented paths
  - `GET /` → 200 with service links
  - `GET /api/v1/withdrawals` → 200
  - `GET /api/v1/withdrawals` without `X-User-Id` → 401 `UNAUTHORIZED`
  - `GET /api/v1/accounts/{id}/ownership` → 200, routed to the mock through Traefik
  - `POST /api/v1/withdrawals` → 201 `COMPLETED`
  - Replay with the same `Idempotency-Key` → 200, same operation id
  - Same key with a different amount → 409 `IDEMPOTENCY_CONFLICT`
  - `GET /api/v1/withdrawals/{id}` → 200
  - `GET /api/v1/withdrawals?status=COMPLETED` → 200
  - `POST /api/v1/withdrawals/{id}/report` on completed → 200
  - `POST /api/v1/withdrawals/{id}/cancel` on completed → 409 `INVALID_STATE`
  - Missing `Idempotency-Key` → 422 `MISSING_IDEMPOTENCY_KEY`
  - Amount `9.99` and `5000.01` → 422 `INVALID_AMOUNT`
- Evidence captured:
  - 18/18 checks passed against the public gateway.
  - Created operation `50fb8667-47cd-49eb-a91e-706e2bc29bee`.
- Known risk or unresolved issue: the public gateway has no authentication; practice-only.
- Next best step: use the API or share the OpenAPI contract, then destroy the stack.

### Session 011

- Date: 2026-11-03
- Goal: Formalize the three-point agreement needed to connect `withdrawal-soles` with the PEN wallet.
- Completed:
  - Added `ACUERDO-INTEGRACION-BILLETERA.md` with decisions for debit ownership, identity mapping, and decimal-to-cents conversion.
  - Documented the proposed withdrawal sequence, wallet error mapping, data columns, reversal policy, and acceptance criteria.
  - Linked the agreement from the README, service reference, and integration contract.
- Verification run:
  - `./init.sh`
- Evidence captured:
  - The agreement explicitly requires `user-service` to expose integer `id_usuario` and the wallet's `/usuarios/{idUsuario}` contract.
  - It records that the wallet's current 503 is an environment issue, not a code failure.
- Commits: pending (integration agreement)
- Files or artifacts updated: `ACUERDO-INTEGRACION-BILLETERA.md`, `README.md`, `service-reference.md`, `withdrawal-soles-integration.md`, `progress.md`
- Known risk or unresolved issue: the agreement needs approval from the users, wallet, and deposits teams; no wallet test account exists yet.
- Next best step: get the public users-service URL and a real active `idUsuario`, then implement the wallet client and schema migration.

### Session 012

- Date: 2026-11-03
- Goal: Tear down the running AWS practice stack to stop charges.
- Completed:
  - Ran `./scripts/destroy-eks-demo.sh` against account `205346659030` in `us-east-1`.
  - Destroyed the platform module (9 resources), then the namespace, ECR images, and the infra module (41 resources), then the EKS CloudWatch log group.
- Verification run:
  - `./scripts/destroy-eks-demo.sh` (exit 0)
  - Post-destroy AWS inventory checks
  - `terraform state list` for both roots
  - `./init.sh`
- Evidence captured:
  - `terraform destroy` (platform): Destroy complete! Resources: 9 destroyed.
  - `terraform destroy` (infra): Destroy complete! Resources: 41 destroyed.
  - `terraform state list`: empty for `infra/terraform` and `infra/platform`.
  - AWS: no EKS clusters, RDS instances, EC2 instances, NAT gateways, ELB/ALB, ECR repositories, tagged VPCs, EBS volumes, EKS log groups, or manual RDS snapshots.
  - The only remaining EIP (`32.199.142.201`) is tagged `machupicchu-eip` and is unrelated to this stack.
- Commits: pending (destroy evidence)
- Files or artifacts updated: `progress.md`, `feature_list.json`, `session-handoff.md`
- Known risk or unresolved issue: `withdrawal-001` and the wallet integration are still unverified against a live environment because the stack is down.
- Next best step: re-apply with `terraform -chdir=infra/terraform apply` and `./scripts/deploy-eks-demo.sh` only when the gateway is needed again.

### Session 013

- Date: 2026-11-06
- Goal: Re-apply the Terraform stack and deploy the application to AWS as requested.
- Completed:
  - Ran `terraform -chdir=infra/terraform init` and `plan` from an empty state: 41 to add.
  - Applied the saved plan in `us-east-1` (account `205346659030`): 41 resources added.
  - Ran `./scripts/deploy-eks-demo.sh`: image `df278ed` built and pushed to ECR, then the platform module applied (10 resources).
- Verification run:
  - `terraform apply` (infra): `Apply complete! Resources: 41 added, 0 changed, 0 destroyed.`
  - `./scripts/deploy-eks-demo.sh` (platform): `Apply complete! Resources: 10 added, 0 changed, 0 destroyed.`
  - `kubectl get nodes`: 2 nodes `Ready` (`v1.35.9-eks-6e7947a`).
  - `kubectl -n withdrawal-soles get pods,svc,ingress`: app 2/2 Running, mock 1/1 Running, migration Completed, Ingress created.
  - Public gateway smoke test: 11/11 passed (`/health`, `/docs`, `/`, 401 without `X-User-Id`, ownership via mock, create 201, idempotent replay 200, get 200, 422 for 9.99 and 5000.01, 422 without `Idempotency-Key`).
- Evidence captured:
  - Gateway: `http://a6c1a4b5ffa8a44808f8a8a0784fe0d7-266125410.us-east-1.elb.amazonaws.com`
  - Withdrawal `77fb4cdd-e0cf-4d7b-ac5a-fbed78f580aa`; status `COMPLETED`.
  - RDS: `app-nube-2-dev-postgres.c2fc66is431b.us-east-1.rds.amazonaws.com:5432`.
  - ECR: `205346659030.dkr.ecr.us-east-1.amazonaws.com/app-nube-2-dev/withdrawal-soles:df278ed`.
- Files or artifacts updated: `feature_list.json`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: the stack is running and billing; the public gateway has no authentication, so it is practice-only.
- Next best step: use the gateway for practice, then run `./scripts/destroy-eks-demo.sh` to stop charges.

### Session 014

- Date: 2026-11-06
- Goal: Integrate `withdrawal-soles` with the published PEN wallet and verify debit, reversal, and error behavior locally and live.
- Completed:
  - Created the `integrate-pen-wallet-debit` OpenSpec change with proposal, design, tasks, and the `pen-wallet-integration` spec.
  - Added wallet settings, domain models/port/exceptions, `amount_to_cents`, JWT signing, and `WalletServiceClient` for `GET /v1/wallets`, `POST /v1/wallets/{walletId}/payments`, and `POST /v1/movements/{movementId}/reverse`.
  - Extended `AccountOwnership` with integer `id_usuario` and parsed `id_usuario`/`idUsuario` in the user-service adapter.
  - Added wallet columns, the `REVERSED` status, repository and mapper support, and Alembic migration `0002_add_wallet_integration`.
  - Debit-in-create with local save compensation and `ReverseWithdrawalUseCase` behind `POST /api/v1/withdrawals/{id}/reverse`.
  - Extended `tools/mock_dependencies.py` with the wallet endpoints and wallets for users 15, 16, and 18; user 17 has no wallet.
  - Added `scripts/simulate_wallet_integration.py`, wallet adapter tests, API debit/reversal tests, and fake wallet fixtures.
  - Regenerated `openapi.yaml` with 7 operations and the reverse endpoint; updated service docs, ERD, and the integration contract.
  - Marked all change tasks complete and archived the change as `2026-11-06-integrate-pen-wallet-debit`; the main specs now include `pen-wallet-integration` and the updated `withdrawal-soles` lifecycle.
- Verification run:
  - `make verify` (ruff + pytest)
  - `scripts/simulate_wallet_integration.py --mode simulate`
  - `scripts/simulate_wallet_integration.py --mode live`
  - `alembic upgrade head` against PostgreSQL 15 in Docker Compose
  - `\d withdrawal_operations` inspection for wallet columns and `ck_status`
  - `make openapi`
  - `openspec validate --all --strict`
  - `./init.sh`
  - `docker compose down -v` after the migration check
- Evidence captured:
  - `make verify`: ruff clean, 83 tests passed.
  - Simulator: 12/12 checks passed.
  - Live wallet: 10/10 checks passed; debit movement `949366f5-5f68-4c78-9f08-ba422ac6f967`, wallet 15 balance `25000 -> 24000 -> 25000` cents after reversal.
  - Migration: `0001 -> 0002_add_wallet_integration`; current head `0002_add_wallet_integration`.
  - Schema: wallet columns present and `ck_status` includes `REVERSED`.
  - OpenAPI: 7 operations including reverse; response includes `wallet_id`, `wallet_movement_id`, and `wallet_reversal_movement_id`.
  - `openspec validate --all --strict`: 7 passed, 0 failed.
  - `./init.sh`: VERIFICATION PASSED, 5/5 harness subsystems and 16/16 checks.
  - `openspec archive integrate-pen-wallet-debit --yes`: archived as `2026-11-06-integrate-pen-wallet-debit`; specs `pen-wallet-integration` created and `withdrawal-soles` updated (2 requirements modified).
- Commits: pending (wallet integration)
- Files or artifacts updated: `src/withdrawal_soles/`, `tests/`, `migrations/versions/0002_add_wallet_integration.py`, `tools/mock_dependencies.py`, `scripts/simulate_wallet_integration.py`, `scripts/export_openapi.py`, `openapi.yaml`, `docs/withdrawal-soles.md`, `service-reference.md`, `withdrawal-soles-integration.md`, `openspec/architecture/`, `openspec/changes/archive/2026-11-06-integrate-pen-wallet-debit/`, `openspec/specs/`, `docker-compose.yml`, `.env.example`, `pyproject.toml`, `feature_list.json`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: the wallet JWT secret is the agreed development secret and is only 18 bytes; production must inject a strong secret. Live wallet calls depend on `http://18.228.136.200` being reachable.
- Next best step: destroy the AWS practice stack with `./scripts/destroy-eks-demo.sh` when it is no longer needed, and redeploy with the new image before testing wallet debit through the gateway.

### Session 015

- Date: 2026-11-06
- Goal: Apply `PARA-INTEGRAR-RETIROS-3.md` to `withdrawal-soles`: JWT-only business routes and the published users-service contract, plus a teammate-facing HTTP checker.
- Completed:
  - Created the `secure-api-jwt-users-contract` OpenSpec change with proposal, design, tasks, and spec deltas.
  - Added mandatory inbound service JWT validation (HS256, issuer `billetera-dev`, subject `retiros`) on every `/api/v1/withdrawals` route; `X-User-Id` remains the end-user identity and is still required.
  - Added `UserIdentity`, `UserNotFound`, `UserInactive`, and `UserServicePort.get_user`; `GET /usuarios/{idUsuario}` now runs before every debit and reversal with the `billetera-service` JWT and the documented 404/422/503 mapping.
  - Added shared service-JWT signing, the users call in the use cases, and the new settings (`USERS_*` and `AUTH_JWT_*`).
  - Extended the mock with `/usuarios/{idUsuario}` and the same JWT verification; Traefik now routes `/usuarios` to the mock.
  - Extended the simulator with auth, users cases, and wallet history; added `scripts/wallet_contract_check.py` and `make contract-check`.
  - Regenerated `openapi.yaml` with the `BearerAuth` scheme and updated the integration documents, service reference, README, `.env.example`, and architecture contract.
  - Archived the change as `2026-11-06-secure-api-jwt-users-contract`; the main specs now include `service-authentication` and the updated wallet/users requirements.
- Verification run:
  - `make verify` (ruff + pytest)
  - `scripts/simulate_wallet_integration.py --mode simulate`
  - `scripts/simulate_wallet_integration.py --mode live`
  - `docker compose up -d --build` and `scripts/wallet_contract_check.py --base-url http://localhost:8080 --wallet-url http://localhost:8080`
  - `make openapi`
  - `openspec validate --all --strict`
  - `./init.sh`
- Evidence captured:
  - `make verify`: ruff clean, 106 tests passed.
  - Simulator: 15/15 checks passed in `simulate` mode; 9/9 in `live` mode with wallet 15 balance `50000 -> 49000 -> 50000` cents.
  - HTTP checker: 11/11 checks passed against the compose stack; debit movement `c8e8ca76-0eb5-4531-9375-75df0ef7f862`; balance restored.
  - Auth: missing token and valid-token-without-`X-User-Id` both return `401 UNAUTHORIZED` with `WWW-Authenticate: Bearer`.
  - Users contract: active user 15 proceeds; active user 19 has no wallet (`WALLET_NOT_FOUND`); inactive user 17 returns `USER_INACTIVE`; unknown user 99 returns `USER_NOT_FOUND`.
  - `openspec validate --all --strict`: 8 passed, 0 failed.
  - `./init.sh`: VERIFICATION PASSED, 5/5 harness subsystems and 16/16 checks.
- Commits: `ff049f2 feat(auth): require service JWT and validate users contract`
- Files or artifacts updated: `src/withdrawal_soles/api/security.py`, `src/withdrawal_soles/api/dependencies.py`, `src/withdrawal_soles/api/errors.py`, `src/withdrawal_soles/core/settings.py`, `src/withdrawal_soles/domain/`, `src/withdrawal_soles/application/use_cases.py`, `src/withdrawal_soles/infrastructure/`, `tests/`, `tools/mock_dependencies.py`, `scripts/simulate_wallet_integration.py`, `scripts/wallet_contract_check.py`, `scripts/export_openapi.py`, `Makefile`, `docker-compose.yml`, `.env.example`, `openapi.yaml`, docs, `openspec/`, `feature_list.json`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: the development secret is shared and only 18 bytes; production must inject a strong secret. The deployed EKS image predates this change, so the gateway must be redeployed before testing JWT and the users contract there.
- Next best step: redeploy the image when the gateway is needed, or destroy the AWS practice stack to stop charges.

### Session 016

- Date: 2026-11-06
- Goal: Destroy the AWS practice stack on request and stop all charges.
- Completed:
  - Ran `./scripts/destroy-eks-demo.sh` against account `205346659030` in `us-east-1`.
  - It destroyed the platform module, removed any remaining namespace and LoadBalancer, deleted the ECR image, then destroyed the infra module and the EKS CloudWatch log group.
- Verification run:
  - `./scripts/destroy-eks-demo.sh` (exit 0)
  - `terraform state list` for `infra/terraform` and `infra/platform`
  - Post-destroy AWS inventory for EKS, RDS, EC2, NAT, ELB/ALB, ECR, tagged VPCs, EBS, and EKS log groups
  - `./init.sh`
- Evidence captured:
  - `Destroy complete! Resources: 41 destroyed.`
  - `terraform state list`: 0 entries in both roots.
  - AWS checks returned no EKS clusters, RDS instances, running EC2 instances, available NAT gateways, ELBv2 or Classic ELBs, ECR repositories, `app-nube-2-dev` VPCs, EBS volumes, or `/aws/eks/app-nube-2-dev-eks` log groups.
  - `./init.sh`: VERIFICATION PASSED, 5/5 harness subsystems and 16/16 checks.
- Commits: `7727c92 chore(infra): destroy the AWS practice stack`
- Files or artifacts updated: `progress.md`, `session-handoff.md`, `feature_list.json`, `service-reference.md`
- Known risk or unresolved issue: none; no billable AWS resources from this stack remain.
- Next best step: keep the local compose stack for development; redeploy with `terraform -chdir=infra/terraform apply` and `./scripts/deploy-eks-demo.sh` only when the gateway is needed again.

### Session 017

- Date: 2026-11-10
- Goal: Bring the local infrastructure back up on request.
- Completed:
  - Rebuilt and started the local Docker Compose stack (`db`, `withdrawal-soles`, `mock-dependencies`, `traefik`).
  - Confirmed Alembic applied `0002_add_wallet_integration` and all service tables exist.
  - Ran the HTTP contract check through Traefik to validate the full withdrawal, wallet debit, reversal, and idempotency flow.
- Verification run:
  - `docker compose up -d --build`
  - `docker compose ps`
  - `curl http://localhost:8080/health`, `/docs`, `http://localhost:8081/dashboard/`
  - `docker compose exec db psql -c '\dt'` and `select version_num from alembic_version`
  - `.venv/bin/python scripts/wallet_contract_check.py --base-url http://localhost:8080 --wallet-url http://localhost:8080`
  - `./init.sh`
- Evidence captured:
  - All four containers `Up`; `db` and `withdrawal-soles` report healthy.
  - `GET /health`: 200 `{"status":"ok"}`; `/docs`: 200; Traefik dashboard: 200.
  - Tables: `withdrawal_operations`, `withdrawal_status_history`, `idempotency_records`, `reporting_attempts`, `alembic_version`; migration `0002_add_wallet_integration`.
  - Contract check: 11/11 checks passed; withdrawal `a8c94465-7653-4883-9130-e3ad3e9dea02` completed, reversed, and balance restored `25000 -> 24000 -> 25000` cents.
- Commits: docs(progress): record local stack bring-up
- Files or artifacts updated: `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: the local stack is for development only; the AWS practice stack remains destroyed.
- Next best step: use `localhost:8080` for development, or re-apply the AWS stack only when the gateway is needed.

### Session 018

- Date: 2026-11-10
- Goal: Bring up the AWS practice stack (EKS, RDS, ECR, Traefik gateway) and make the deployed service fully functional.
- Completed:
  - Applied `infra/terraform`: 41 resources added (VPC, subnets, NAT, EKS 1.35, node group, IAM, security groups, ECR, private RDS PostgreSQL 15).
  - Ran `./scripts/deploy-eks-demo.sh`: built and pushed image tag `c3f8fd7`, applied the platform module (Traefik via Helm, namespace, DB secret, Alembic job, app and mock deployments, ingress), updated kubeconfig.
  - Found and fixed two platform gaps that broke the wallet flow in AWS:
    - `infra/platform/ingress.tf` did not route `/usuarios` or `/v1/` (wallet) to `mock-dependencies`; added both prefix paths.
    - `infra/platform/app.tf` did not set `WITHDRAWAL_SOLES_WALLET_SERVICE_URL`, so the app fell back to the external `18.228.136.200` and returned `503 DEPENDENCY_UNAVAILABLE`; it now points at the in-cluster Traefik service.
  - Updated `infra/platform/README.md` for the new mock routes and the self-contained service URLs.
- Verification run:
  - `terraform -chdir=infra/terraform plan` and `apply`
  - `./scripts/deploy-eks-demo.sh`
  - `kubectl -n withdrawal-soles get pods,svc,ingress` and `kubectl get nodes`
  - `curl http://<gateway>/health`
  - `scripts/wallet_contract_check.py --base-url http://<gateway> --wallet-url http://<gateway>`
  - `terraform fmt -check -recursive infra` and `./scripts/verify-terraform.sh`
  - `./init.sh`
- Evidence captured:
  - Plan: 41 to add; apply complete. Platform apply: 10 resources; ingress fix: 1 change; wallet env fix: 1 change.
  - EKS `app-nube-2-dev-eks` active with 2 `Ready` `t3.small` nodes (`v1.35.9-eks-8418f54`); RDS `app-nube-2-dev-postgres` `db.t4g.micro` available; NAT gateway available; ECR repo `app-nube-2-dev/withdrawal-soles`.
  - Pods: 2/2 app replicas Running, mock Running, migration Job Completed.
  - Gateway `http://a0f4e669772d6496a9125e3de34cffbc-795710705.us-east-1.elb.amazonaws.com`: `/health` 200.
  - Contract check: 11/11 passed; withdrawal `a4fe9755-c44f-4828-9a3e-e215da7a161a` completed and reversed; balance `25000 -> 24000 -> 25000` cents.
  - `terraform fmt` clean; `verify-terraform.sh` valid; `./init.sh` VERIFICATION PASSED.
- Commits: `fix(infra): route mock users/wallet paths and set wallet URL on EKS`, `docs(progress): record AWS stack bring-up`
- Files or artifacts updated: `infra/platform/ingress.tf`, `infra/platform/app.tf`, `infra/platform/README.md`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: the stack costs roughly $157/month while running; the gateway is public and unauthenticated at the edge; Terraform state is local.
- Next best step: run `./scripts/destroy-eks-demo.sh` when the practice run ends to stop charges.

### Session 019

- Date: 2026-11-10
- Goal: Publish the withdrawal-soles contract for the colleague and consume the published Billetera Digital PEN API v1.1.0 end to end.
- Completed:
  - Moved the generated contract to `api/openapi.yaml` (the location the operator chose), updated `scripts/export_openapi.py`, and regenerated it from the current app: 7 operations, `BearerAuth`, current gateway URL.
  - Added `api/openapi-service2.yaml` as the reference contract for the consumed wallet API.
  - Pointed the wallet integration at the new published base `http://52.67.162.209` in settings, `.env.example`, docs, scripts, and the integration agreement.
  - Added `wallet_service_url` to the platform module (default `http://52.67.162.209`) and wired it into the EKS deployment.
  - Deployed image `28b1e55` and verified the real wallet flow through the AWS gateway.
- Verification run:
  - `curl http://52.67.162.209/health` and `/health/ready`
  - `GET /v1/wallets?idUsuario=15` against the published wallet
  - `make openapi` and path comparison against the live `/openapi.json`
  - `./scripts/deploy-eks-demo.sh` (image `28b1e55`)
  - `kubectl -n withdrawal-soles rollout status`, pod list, and deployment env inspection
  - `scripts/wallet_contract_check.py --base-url http://<gateway> --wallet-url http://52.67.162.209`
  - Negative test: `amount=1000.00` against a 250.00 balance
  - `GET /v1/wallets/{id}/movements` on the published wallet and `GET /api/v1/withdrawals` on our API
  - `make verify`, `terraform fmt -check -recursive infra`, `./scripts/verify-terraform.sh`, `./init.sh`
- Evidence captured:
  - Published wallet health 200 and ready 200; user 15 wallet `b0414364-5b65-4881-89ad-6ecbf2e99bb4`, balance `25000` cents.
  - Contract check through the AWS gateway: 11/11; withdrawal `74e2f8e7-a36e-417d-b781-1af20d15ada9` completed, debited, reversed, and balance restored `25000 -> 24000 -> 25000`.
  - Published wallet movements: `PAYMENT` debit `7bc4cef5-9a05-49af-8bc0-f51eb3d6a325` with `externalReference` equal to our withdrawal id, then `REVERSAL` credit `849ab4e0-3120-48cf-b839-eb09e0e00826` with `reversalOf` pointing at the payment.
  - Our API stores `wallet_id=b0414364-...`, `wallet_movement_id=7bc4cef5-...`, `wallet_reversal_movement_id=849ab4e0-...`, status `REVERSED`.
  - Insufficient balance maps to `422 INSUFFICIENT_BALANCE` with no debit.
  - `api/openapi.yaml` paths match the live `/openapi.json`; servers point at the current gateway, `localhost:8080`, and `localhost:18080`.
  - `make verify`: ruff clean, 106 tests passed; Terraform format and validate clean; `./init.sh` VERIFICATION PASSED.
- Commits: `28b1e55 feat(wallet): consume the published Billetera API v1.1.0`, `docs(progress): record published wallet integration`
- Files or artifacts updated: `api/openapi.yaml`, `api/openapi-service2.yaml`, `scripts/export_openapi.py`, `src/withdrawal_soles/core/settings.py`, `.env.example`, `docs/withdrawal-soles.md`, `service-reference.md`, `withdrawal-soles-integration.md`, `ACUERDO-INTEGRACION-BILLETERA.md`, `scripts/wallet_contract_check.py`, `scripts/simulate_wallet_integration.py`, `infra/platform/app.tf`, `infra/platform/variables.tf`, `infra/platform/README.md`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: the published wallet is an external dependency outside our control; its availability gates withdrawals. The shared development JWT secret is still 18 bytes.
- Next best step: send `api/openapi.yaml` to the wallet team and keep `wallet_service_url` configurable per environment.

### Session 020

- Date: 2026-11-10
- Goal: Rewrite the root README around the single implemented service and publish it to GitHub.
- Completed:
  - Rewrote `README.md` to scope the repository to `withdrawal-soles` only: responsibilities, domain rules, tech stack, HTTP contract, local commands, and AWS infrastructure.
  - Embedded the owned-database ERD (`withdrawal_soles_db`) with constraints and the status lifecycle.
  - Removed the broken link to the moved `ACUERDO-INTEGRACION-BILLETERA.md` and pointed documentation at existing files.
  - Added `origin` (`J0sePs/app-microservices-spec`) and merged the remote initial history with `--allow-unrelated-histories` (`-X ours`), then pushed `main`.
- Verification run:
  - `./init.sh` — VERIFICATION PASSED (5/5 subsystems, 106 tests).
  - `git push -u origin main` — `77e4296..47c5b04`.
- Evidence captured:
  - README renders an `erDiagram` for `withdrawal_operations`, `withdrawal_status_history`, `idempotency_records`, and `reporting_attempts`.
  - Remote `main` now contains the local history.
- Commits: `81d37b5 docs(readme): focus on withdrawal-soles with ERD and service details`, merge commit `chore: merge remote initial OpenSpec history`
- Files or artifacts updated: `README.md`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: the five moved integration drafts remain deleted in the working tree (`temp/` is untracked) and were not committed; `service-reference.md` and `withdrawal-soles-integration.md` still link to `ACUERDO-INTEGRACION-BILLETERA.md`.
- Next best step: decide whether to restore or permanently remove the moved integration drafts and fix their remaining links.

### Session 021

- Date: 2026-11-10
- Goal: Add a Postman collection that tests both `withdrawal-soles` and the teammate's Billetera Digital PEN API.
- Completed:
  - Added `postman/withdrawal-soles-billetera.postman_collection.json` with three folders: my service, the Billetera PEN contract, and an integrated end-to-end flow.
  - Added a collection pre-request script that signs the HS256 service JWT automatically (`iss=billetera-dev`, `sub=retiros`) using Postman's built-in `crypto-js`.
  - Added test scripts that capture `withdrawal_id`, `wallet_id`, `movement_id`, and balances between requests.
  - Added `postman/README.md` with import steps, variables, idempotency notes, and the local-stub versus published-API difference.
  - Linked the collection from the root `README.md`.
- Verification run:
  - `python3 -m json.tool postman/withdrawal-soles-billetera.postman_collection.json`
  - Safe smoke run with Newman against the live stack (5 requests, 6 assertions, 0 failures).
  - Full collection with Newman against the local wallet stub (25 requests, 0 request failures; all withdrawal and integrated-flow assertions passed; the only failures were wallet-contract routes the local stub does not implement).
  - `./init.sh` — VERIFICATION PASSED (106 tests).
- Evidence captured:
  - Withdrawal folder: create `201`, list `200`, get `200`, cancel `409` (already completed), reverse `200`, report `409` (already reversed).
  - Integrated flow: wallet lookup, withdrawal create, movement visible with `externalReference` equal to the withdrawal id, reverse `200`, balance restored.
- Commits: `test(postman): add withdrawal-soles and Billetera PEN collection`
- Files or artifacts updated: `postman/withdrawal-soles-billetera.postman_collection.json`, `postman/README.md`, `README.md`, `progress.md`, `session-handoff.md`
- Known risk or unresolved issue: the local wallet stub only implements a subset of the friend's API, so the full wallet folder must run against `http://52.67.162.209`.
- Next best step: share the collection with the teammate and adjust `wallet_user_id`/`wallet_id` to their test data.

### Session 022

- Date: 2026-11-10
- Goal: Publish the integration drafts that had been moved to `temp/`.
- Completed:
  - Committed the move of `ACUERDO-INTEGRACION-BILLETERA.md` and the four
    `PARA-*` drafts into `temp/`, so the repository matches the working tree.
  - Updated the two remaining links to the wallet agreement so they point at
    `temp/ACUERDO-INTEGRACION-BILLETERA.md`.
- Verification run:
  - `git status --short` confirms only the intended move and link edits.
  - `./init.sh` passed.
- Evidence captured:
  - `temp/` contains the five integration documents; no Terraform state,
    `.tfvars`, `.env`, or AWS credentials were staged.
- Commits: `docs: move integration drafts to temp`
- Files or artifacts updated: `temp/`, `service-reference.md`,
  `withdrawal-soles-integration.md`, `progress.md`
- Known risk or unresolved issue: none.
- Next best step: keep new drafts in `docs/` or `temp/`, never in the root.

### Session 023

- Date: 2026-11-10
- Goal: Tear down the AWS practice stack to stop billing.
- Completed:
  - Ran `./scripts/destroy-eks-demo.sh`, which destroyed `infra/platform`
    first (9 resources: Traefik, namespaces, app/mock deployments, services,
    secret, migration job, ingress), removed the `withdrawal-soles` namespace
    and its Classic LoadBalancer, deleted the ECR images, then destroyed
    `infra/terraform` (41 resources: EKS, node group, RDS, ECR, VPC, NAT, IGW,
    subnets, IAM, SGs), and deleted the EKS CloudWatch log group.
- Verification run:
  - `terraform -chdir=infra/terraform state list` and
    `terraform -chdir=infra/platform state list`: both empty.
  - AWS CLI post-destroy sweep in `us-east-1`: no EKS clusters, RDS
    instances, ECR repositories, tagged VPCs, NAT gateways, ELB/ALB, tagged
    EBS volumes, tagged security groups, or `/aws/eks` log groups.
  - `./init.sh` — VERIFICATION PASSED.
- Evidence captured:
  - `infra/platform`: `Destroy complete! Resources: 9 destroyed`.
  - `infra/terraform`: `Destroy complete! Resources: 41 destroyed`.
  - The only remaining Elastic IP, `32.199.142.201`, is tagged
    `machupicchu-eip` and is unrelated to this stack; it was left untouched.
- Commits: (this session)
- Files or artifacts updated: `progress.md`, `session-handoff.md`,
  `feature_list.json`
- Known risk or unresolved issue: local Docker Compose stack and the external
  Billetera PEN dependency are unaffected; no AWS compute remains.
- Next best step: redeploy with `terraform -chdir=infra/terraform apply` and
  `./scripts/deploy-eks-demo.sh` only when a practice run is needed.

### Session 024

- Date: 2026-11-13
- Goal: Deploy the `withdrawal-soles` practice stack on AWS and verify it end to end.
- Completed:
  - Confirmed a clean starting point: valid credentials for account
    `205346659030`, empty Terraform states, no EKS/RDS/ECR resources.
  - `terraform -chdir=infra/terraform apply` from a saved plan:
    `41 added, 0 changed, 0 destroyed` (VPC, 2 public + 2 private subnets, NAT,
    EKS `app-nube-2-dev-eks` on v1.35, 2 × `t3.small` nodes, ECR, private RDS
    PostgreSQL 15.17, IAM, SGs).
  - `./scripts/deploy-eks-demo.sh` pushed image `4636058` to ECR and applied
    `infra/platform` (10 resources): Traefik 42.2.0, namespace, DB secret,
    migration Job `Completed`, 2/2 `withdrawal-soles` pods, 1/1
    `mock-dependencies`, Ingress, public Classic LoadBalancer.
  - Found the published wallet `http://52.67.162.209` unreachable (TCP timeout
    on port 80) and, with the owner's approval, pointed
    `wallet_service_url` at the in-cluster Traefik mock for this practice run.
  - Added an opt-in `WALLET_SERVICE_URL` override to
    `scripts/deploy-eks-demo.sh` so the wallet target can be chosen without
    editing Terraform; documented it in `infra/terraform/README.md` and
    `infra/platform/README.md`.
- Verification run:
  - `kubectl get nodes`: 2 nodes `Ready` (v1.35.9-eks-8418f54).
  - `kubectl -n withdrawal-soles get pods,svc,ingress`: app 2/2 Running, mock
    1/1 Running, migration Job Completed, Ingress with the ELB address.
  - `GET /health`, `/docs`, `/openapi.json`, `/` through the gateway: 200.
  - `scripts/wallet_contract_check.py --base-url <gateway> --wallet-url <gateway>`:
    11/11 checks passed (401 without token, 401 without `X-User-Id`, list,
    wallet balance 25000 cents, create 201 COMPLETED, replay 200 same id,
    debit 25000 → 24000, reverse 200 REVERSED, second reverse 422, balance
    restored to 25000).
  - Domain limits through the gateway: `9.99` → 422 `INVALID_AMOUNT`,
    `5000.01` → 422 `INVALID_AMOUNT`, `10.00` → 201 COMPLETED,
    missing `Idempotency-Key` → 422 `MISSING_IDEMPOTENCY_KEY`; the S/ 10.00
    operation `b2d17e3f-9569-4330-95f0-3af67444150a` was reversed (200 REVERSED)
    and the balance restored.
  - Pod environment: DB URL on
    `app-nube-2-dev-postgres.c2fc66is431b.us-east-1.rds.amazonaws.com:5432`;
    wallet and users clients on `http://traefik.traefik.svc.cluster.local`.
  - `aws rds describe-db-instances`: `available`, PostgreSQL 15.17,
    `PubliclyAccessible=false`; ECR holds image `4636058`.
  - `./init.sh`: VERIFICATION PASSED (5/5 subsystems, 16/16 checks; 106 tests).
- Evidence captured:
  - `terraform apply` (infra): `Apply complete! Resources: 41 added`.
  - `terraform apply` (platform): `Apply complete! Resources: 10 added`.
  - Gateway: `http://abc44d73ea94740738c53880a3469936-1565234038.us-east-1.elb.amazonaws.com`.
  - Contract checker: `Summary: 11/11 checks passed`.
- Commits: (this session)
- Files or artifacts updated: `scripts/deploy-eks-demo.sh`,
  `infra/terraform/README.md`, `infra/platform/README.md`, `progress.md`,
  `feature_list.json`, `session-handoff.md`
- Known risk or unresolved issue: the stack is billable (~$157/month while it
  runs) and the gateway is public with no edge authentication, so it is
  practice-only. The wallet target is the in-cluster stub, not the published
  Billetera PEN API, because the latter is down.
- Next best step: run `./scripts/destroy-eks-demo.sh` when the practice run
  ends; restore the published wallet URL afterwards once it is reachable.

### Session 025

- Date: 2026-11-13
- Goal: Prepare CI/CD from GitHub Actions to the shared EKS cluster, where the
  service consumes `billetera-api` (namespace `billetera`, port `3000`).
- Completed:
  - Created OpenSpec change `cicd-eks-deploy` (proposal, design, tasks, deltas
    for `continuous-delivery`, `aws-platform-infrastructure`, and
    `eks-application-platform`) and feature `cicd-001` (`in_progress`).
  - `.github/workflows/verify.yml`: `checks` (`make lint`, `make test`,
    `make openapi-check`), `verify` (`./init.sh`), `terraform`, and, on `main`
    with `EKS_DEPLOY_ENABLED=true`, `image` (ECR `<sha>` + `latest`) and
    `deploy` (`terraform apply` on `infra/platform`, kubeconfig, rollout,
    image check, `/health`).
  - S3 backend for both roots (`scripts/bootstrap-tf-state.sh`,
    `scripts/tf-init.sh`); platform reads infra state from S3.
  - ECR `IMMUTABLE_WITH_EXCLUSION` for `latest`, lifecycle policy,
    `ecr_repository_name` output, optional `cluster_admin_principal_arns`.
  - Platform: wallet default `http://billetera-api.billetera.svc.cluster.local:3000`,
    `wallet_mock_enabled`, `mock_dependencies_enabled`, `withdrawal-jwt`
    Secret with issuer `billetera-dev`.
  - Supporting fix: indentation in `openspec/config.yaml` (OpenSpec ignored
    the file).
- Verification run:
  - `./scripts/verify-terraform.sh`, `make verify` (106 passed),
    `make openapi-check` (OK; injected drift exits 2),
    `openspec validate --all --strict` (9/9), `./init.sh` (PASSED).
  - `terraform console` for the three toggle combinations.
  - Read-only `terraform plan` of the new code against the live local states
    (scratch copy, `-lock=false`): infra `1 add, 1 change, 0 destroy`;
    platform with `wallet_mock_enabled=true` `2 add, 1 change, 0 destroy`
    (JWT Secret, migration Job re-run, Deployment env; mock moved to `[0]`;
    Ingress unchanged).
- Evidence captured: see `cicd-001` in `feature_list.json`.
- Commits: `feat(cicd): deploy main to the shared EKS cluster from GitHub Actions`
  on branch `feature/cicd-eks-deploy`.
- Known risk or unresolved issue: the live stack still uses local state; the
  next apply needs `scripts/tf-init.sh <module> -migrate-state`. `billetera`
  namespace does not exist yet, so deploys need `WALLET_MOCK_ENABLED=true`.
  `actionlint` was not run (blocked by the local permission policy).
- Next best step: bootstrap the state bucket, migrate both states, register the
  GitHub secrets and variables, merge the PR, and confirm the first CI deploy.
- Follow-up (same session): created `s3://app-nube-2-tfstate-205346659030`
  with `scripts/bootstrap-tf-state.sh` (versioning, AES256, public access
  block), backed up both local states, and migrated them with
  `scripts/tf-init.sh <module> -migrate-state -force-copy`. Verified the S3
  objects and `terraform state list` through S3 (infra 45 entries, platform
  12); the local state files are now empty. Credentialed plan through S3:
  `1 to add, 1 to change, 0 to destroy` (not applied). Registered the GitHub
  variable `TF_STATE_BUCKET`. Documented that `-force-copy` is required for the
  one-time migration because `tf-init.sh` runs with `-input=false`.
- Follow-up (same session): created the least-privilege IAM user
  `github-actions-withdrawal-soles` with `scripts/bootstrap-ci-user.sh`
  (inline policy: ECR push for this repository, `eks:DescribeCluster`, S3 state
  objects), added it to `cluster_admin_principal_arns` in the ignored
  `terraform.tfvars`, and applied `infra/terraform` from a saved plan:
  `Apply complete! Resources: 3 added, 1 changed, 0 destroyed`. ECR now reports
  `IMMUTABLE_WITH_EXCLUSION` with the `latest` wildcard. The CI key was created
  and stored straight into GitHub secrets; with that key, S3 state, ECR, and
  `eks describe-cluster` (ACTIVE) succeed. Stored `AWS_REGION`, `DB_PASSWORD`
  (from the ignored tfvars), `JWT_SECRET`, and the variable
  `WALLET_MOCK_ENABLED=true`. `EKS_DEPLOY_ENABLED` is intentionally unset.
- Follow-up (same session): set `EKS_DEPLOY_ENABLED=true` and merged PR #2.
  Run `43502259584` built and pushed the image but the platform apply failed
  with "Provider produced inconsistent final plan" (computed annotation); PR #3
  switched to `var.jwt_secret_version`. Run `43503232677` applied and rolled
  out `:6f14df1…`; only the image check failed because GitHub drops job outputs
  containing a secret value (`AWS_REGION` appears in the ECR URL). Manual
  verification: 2/2 app pods on the new image, `/health` 200, contract check
  11/11. `fix/ci-image-check` compares against the platform output inside the
  deploy job.
