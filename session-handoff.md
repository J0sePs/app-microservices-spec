# Session Handoff

## Verified Now

- `withdrawal-001` and `infra-001` are `passing` with recorded evidence.
- `make verify` passes: ruff clean and 54 tests pass.
- `./init.sh` passes with 5/5 harness subsystems and 16/16 checks.
- `./scripts/verify-terraform.sh` passes: fmt, init, and validate.
- A credentialed `terraform plan` renders 35 resources: VPC, subnets, NAT, EKS, node group, ECR, RDS, IAM, security groups, and outputs.
- The local Docker Compose stack is healthy and `GET /health` returns 200.
- No AWS resources were created; `terraform apply` was not run.
- `provision-aws-eks-terraform` is archived as
  `2026-10-30-provision-aws-eks-terraform`, and
  `openspec/specs/aws-platform-infrastructure/spec.md` exists.

## Changed This Session

- Added `infra/terraform/` with the complete AWS target topology.
- Added variable validation, sensitive database inputs, outputs, example tfvars, and the Terraform README.
- Added `scripts/verify-terraform.sh` and a credential-free Terraform CI job.
- Updated the root README and architecture deployment notes.
- Rewrote `openspec/config.yaml` with the full project context and rules.
- Archived `provision-aws-eks-terraform` and created the
  `aws-platform-infrastructure` main spec.

## Broken Or Unverified

- Application deployment, Traefik on EKS, and Kubernetes manifests are not implemented.
- Terraform uses local state; an S3 backend with locking is still required for shared use.
- RDS is single-AZ and the VPC has one NAT gateway; both are development defaults.
- No `terraform apply` has been approved, so the cluster is not running in AWS.

## Next Best Step

Keep the application running locally. Deploy with `terraform apply` only after the account owner approves the EKS, EC2, NAT, and RDS cost. Then configure kubectl and add the application deployment manifests as a separate change.

## Commands

```bash
./init.sh
./scripts/verify-terraform.sh
openspec validate --all --strict
docker compose up -d --build
curl http://localhost:8080/health
```
