# Session Handoff

## Verified Now

- `withdrawal-001` and `infra-001` are `passing` with recorded evidence.
- `make verify` passes: ruff clean and 55 tests pass.
- `./init.sh` passes with 5/5 harness subsystems and 16/16 checks.
- `openapi.yaml` is generated from the FastAPI app and `make openapi` is available.
- The AWS practice stack was destroyed on 2026-10-30:
  - Terraform state is empty and outputs are `{}`.
  - No EKS clusters, RDS instances, EC2 instances, NAT gateways, ELBs, ECR
    repositories, tagged VPCs, EBS volumes, or EKS log groups remain.
- The local Docker Compose stack remains healthy on port `8080`.

## Changed This Session

- Deleted the `withdrawal-soles` Kubernetes namespace and its LoadBalancer.
- Deleted the ECR image and completed `terraform destroy`.
- Deleted the EKS CloudWatch log group.
- Added `scripts/destroy-eks-demo.sh` for clean teardown.
- Recorded the public deployment and teardown evidence in `feature_list.json`
  and `progress.md`.

## Broken Or Unverified

- The application is not running in AWS; only the local Docker Compose stack is
  available.
- Terraform uses local state; an S3 backend with locking is still required for
  shared use.
- The public practice endpoint no longer exists.

## Next Best Step

Use the local stack for development. To practice on AWS again, run
`terraform apply` and `./scripts/deploy-eks-demo.sh`; when finished, always run
`./scripts/destroy-eks-demo.sh` to stop EKS, EC2, NAT, RDS, and ELB charges.

## Commands

```bash
./init.sh
make verify
make openapi
docker compose up -d --build
curl http://localhost:8080/docs

cd infra/terraform && terraform apply
./scripts/deploy-eks-demo.sh
./scripts/destroy-eks-demo.sh
```
