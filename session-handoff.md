# Session Handoff

## Verified Now

- `withdrawal-001` and `infra-001` are `passing` with recorded evidence.
- `make verify` passes: ruff clean and 55 tests pass.
- `./init.sh` passes with 5/5 harness subsystems and 16/16 checks.
- `./scripts/verify-terraform.sh` passes: fmt, init, and validate.
- The AWS stack is deployed in `us-east-1`: VPC, 2 `t3.small` nodes, EKS 1.35
  (`STANDARD` support), ECR, and private RDS PostgreSQL 15.
- `terraform plan -detailed-exitcode` reports no changes after apply.
- The application runs in EKS with 2/2 replicas, the mock dependency, and a
  completed migration Job.
- `GET /health` and `GET /docs` return 200 through
  `kubectl port-forward` on port `18080`.
- A real withdrawal returned `201 COMPLETED` with transaction
  `ce802eb6-e775-473a-8620-f46e4a873caf`.
- The app is publicly reachable at
  `http://af7095da6a12e43adba0fe33f0c5087d-176028442.us-east-1.elb.amazonaws.com`
  (current IP `54.173.162.134`). Public `/health` and `/docs` return 200, and a
  public withdrawal returned `201 COMPLETED` with transaction
  `f52daa2d-d767-4d0e-959b-b0660319ce7d`.
- The local Docker Compose stack also remains healthy on port `8080`.

## Changed This Session

- Fixed the EKS node and EKS-managed cluster security-group egress rules.
- Set EKS upgrade support to `STANDARD`.
- Resolved the RDS Free Tier restriction with backup retention `0` and
  20 GiB maximum storage.
- Built and pushed image
  `205346659030.dkr.ecr.us-east-1.amazonaws.com/app-nube-2-dev/withdrawal-soles:3aac6c0`.
- Deployed `withdrawal-soles` and `mock-dependencies` to namespace
  `withdrawal-soles`.
- Added a root route to the FastAPI app so `/` returns service links.
- Updated evidence, progress, and Terraform documentation.

## Broken Or Unverified

- The public LoadBalancer is a practice-only endpoint with no gateway
  authentication; the service trusts `X-User-Id`, so callers can impersonate a
  user. Do not expose real data.
- Terraform still uses local state; an S3 backend with locking is required for
  shared use.
- RDS is single-AZ and the VPC has one NAT gateway; both are development
  defaults.
- The AWS stack is running and billing approximately **$0.25/hour** plus data,
  including the Classic LoadBalancer.

## Next Best Step

Practice against the public `/docs` endpoint, then run `terraform destroy` and
confirm EKS, EC2, NAT, RDS, and the LoadBalancer are gone.

## Commands

```bash
./init.sh
./scripts/verify-terraform.sh
openspec validate --all --strict

aws eks update-kubeconfig --region us-east-1 --name app-nube-2-dev-eks
kubectl -n withdrawal-soles get pods
kubectl -n withdrawal-soles port-forward svc/withdrawal-soles 18080:80
curl http://localhost:18080/health

cd infra/terraform && terraform destroy
```
