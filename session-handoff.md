# Session Handoff

## Verified Now

- `withdrawal-001`, `infra-001`, and `platform-001` are `passing` with evidence.
- `./init.sh` passes with 5/5 harness subsystems and 16/16 checks.
- The AWS practice stack is **running and billing** since 2026-11-06 in
  `us-east-1`, account `205346659030`:
  - infra: 41 resources (VPC, EKS `app-nube-2-dev-eks` v1.35, 2 × `t3.small`
    nodes Ready, ECR, RDS PostgreSQL 15).
  - platform: 10 resources (Traefik 42.2.0 2/2, app 2/2, mock 1/1, migration
    Job Completed, Ingress).
  - Gateway: `http://a6c1a4b5ffa8a44808f8a8a0784fe0d7-266125410.us-east-1.elb.amazonaws.com`
  - Public smoke test: 11/11 passed, including create 201 `COMPLETED`,
    idempotent replay 200, and 401/422 error paths.
- The local Docker Compose stack is not running; `localhost:8080` is down.

## Changed This Session

- Re-applied `infra/terraform` (41 resources) and ran
  `./scripts/deploy-eks-demo.sh` (platform, 10 resources).
- Recorded deploy and smoke-test evidence in `feature_list.json` and
  `progress.md`.

## Broken Or Unverified

- The stack is up and costs about $0.22/hour (~$5.20/day). It must be destroyed
  when practice ends.
- The public gateway has no authentication; practice-only.
- Terraform uses local state; an S3 backend with locking is required for shared
  use.

## Next Best Step

Use the gateway for practice, then stop charges:

```bash
./scripts/destroy-eks-demo.sh
```

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
