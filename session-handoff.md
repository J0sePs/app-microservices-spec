# Session Handoff

## Verified Now

- `withdrawal-001`, `infra-001`, and `platform-001` are `passing` with evidence.
- `make verify` passes: ruff clean and 55 tests pass.
- `./init.sh` passes with 5/5 harness subsystems and 16/16 checks.
- `openapi.yaml` is generated from the FastAPI app; `make openapi` regenerates it.
- `terraform-eks-platform` is archived as `2026-10-30-terraform-eks-platform`;
  `openspec/specs/eks-application-platform/spec.md` exists.
- The AWS stack is currently running:
  - EKS 1.35 with two ready `t3.small` nodes.
  - RDS PostgreSQL 15 and ECR are active.
  - Traefik 2/2, application 2/2, mock 1/1, migration Job Complete.
  - Gateway: `http://aa56b06084cae4b828ba4a1f30f3ceb6-2084714021.us-east-1.elb.amazonaws.com`
  - Gateway `/health`, `/docs`, and `/` return 200.
  - A withdrawal through the gateway returned `201 COMPLETED` with transaction
    `614bd3f4-718d-4860-8b23-49b3e9b6e783`.
- The local Docker Compose stack remains healthy on port `8080`.

## Changed This Session

- Re-applied both Terraform roots: 41 infra resources and 10 platform resources.
- Updated `scripts/deploy-eks-demo.sh` to run `aws eks update-kubeconfig`
  automatically for the new cluster.
- Updated `service-reference.md` with the current gateway URL.
- Recorded the redeploy evidence in `feature_list.json` and `progress.md`.

## Broken Or Unverified

- The public gateway has no gateway authentication and trusts `X-User-Id`; it is
  practice-only. Do not use real data.
- Terraform uses local state; an S3 backend with locking is required for shared
  use.
- The stack is running and billing approximately **$0.25/hour** plus data.

## Next Best Step

Use the gateway for practice. When finished, run:

```bash
./scripts/destroy-eks-demo.sh
```

It destroys the platform first, then the infra, deletes ECR images, and removes
the EKS log group.

## Commands

```bash
./init.sh
make verify
./scripts/verify-terraform.sh
make openapi
docker compose up -d --build
curl http://localhost:8080/docs

# AWS deployment
terraform -chdir=infra/terraform apply
./scripts/deploy-eks-demo.sh
terraform -chdir=infra/platform output -raw gateway_url

# AWS teardown
./scripts/destroy-eks-demo.sh
```
