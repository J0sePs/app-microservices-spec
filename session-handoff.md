# Session Handoff

## Verified Now

- `withdrawal-001`, `infra-001`, and `platform-001` are `passing` with evidence.
- `make verify` passes: ruff clean and 55 tests pass.
- `./init.sh` passes with 5/5 harness subsystems and 16/16 checks.
- `openapi.yaml` is generated from the FastAPI app; `make openapi` regenerates it.
- `terraform-eks-platform` is archived as `2026-10-30-terraform-eks-platform`;
  `openspec/specs/eks-application-platform/spec.md` exists.
- The AWS practice stack was destroyed on 2026-11-03 and is no longer billing:
  - `terraform destroy` removed 9 platform and 41 infra resources.
  - Both Terraform states are empty; the ECR images and EKS log group are gone.
  - AWS checks show no EKS, RDS, EC2, NAT gateway, ELB, ECR, tagged VPC, EBS,
    manual RDS snapshot, or EKS log group remains.
  - The only remaining EIP (`32.199.142.201`) is tagged `machupicchu-eip` and is
    unrelated to this stack.
- The local Docker Compose stack remains healthy on port `8080`.

## Changed This Session

- Ran `./scripts/destroy-eks-demo.sh` and recorded the teardown evidence in
  `feature_list.json` and `progress.md`.

## Broken Or Unverified

- The stack is down, so the gateway URL from the previous session is dead and
  `withdrawal-001` cannot be exercised against AWS until it is re-applied.
- Terraform uses local state; an S3 backend with locking is required for shared
  use.

## Next Best Step

Nothing is running. To practise against the cloud again:

```bash
terraform -chdir=infra/terraform apply
./scripts/deploy-eks-demo.sh
```

Then destroy it again with `./scripts/destroy-eks-demo.sh` when finished.

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
