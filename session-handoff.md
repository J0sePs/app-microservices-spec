# Session Handoff

## Verified Now

- `withdrawal-001`, `infra-001`, and `platform-001` are `passing` with evidence.
- `make verify` passes: ruff clean and 55 tests pass.
- `./init.sh` passes with 5/5 harness subsystems and 16/16 checks.
- `openapi.yaml` is generated from the FastAPI app; `make openapi` regenerates it.
- `terraform-eks-platform` is archived as `2026-10-30-terraform-eks-platform`;
  `openspec/specs/eks-application-platform/spec.md` exists.
- `infra/platform/` deploys Traefik, the namespace, database Secret, migration
  Job, application, mock, Services, Ingress, and gateway outputs.
- The platform was applied and verified live:
  - Traefik 2/2, application 2/2, mock 1/1, migration Job Complete.
  - Gateway `/health`, `/docs`, and `/` returned 200.
  - A withdrawal through the gateway returned `201 COMPLETED`.
- The platform and infra were then destroyed:
  - Terraform states are empty and outputs are `{}`.
  - No EKS, RDS, EC2, available NAT, ELB/ALB, ECR, tagged VPC, EBS,
    RDS snapshot, or EKS log group remains.
  - The remaining EIP `32.199.142.201` belongs to `machupicchu-eip`.
- The local Docker Compose stack remains healthy on port `8080`.

## Changed This Session

- Added `infra/platform/` with Kubernetes/Helm providers, pinned Traefik chart
  `42.2.0`, application and mock workloads, migration Job, Ingress, and outputs.
- Updated the deploy script to apply Terraform instead of ad-hoc `kubectl`.
- Updated the destroy script to tear down the platform before the infra.
- Updated the Terraform verification script to check both roots.
- Fixed the double-base64 database Secret and added Job replacement on Secret
  changes.
- Recorded the live gateway deployment and full teardown.

## Broken Or Unverified

- The application is not running in AWS; only the local Docker Compose stack is
  available.
- Terraform uses local state; an S3 backend with locking is required for shared
  use.
- The public gateway had no authentication and trusted `X-User-Id`; it was
  practice-only and no longer exists.

## Next Best Step

Use the local stack for development. To practice on AWS again, apply the infra,
then run `./scripts/deploy-eks-demo.sh`; always finish with
`./scripts/destroy-eks-demo.sh`.

## Commands

```bash
./init.sh
make verify
./scripts/verify-terraform.sh
make openapi
docker compose up -d --build
curl http://localhost:8080/docs

terraform -chdir=infra/terraform apply
./scripts/deploy-eks-demo.sh
./scripts/destroy-eks-demo.sh
```
