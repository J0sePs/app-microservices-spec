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

- No LoadBalancer or public application URL exists; the app Service is
  `ClusterIP` and is exposed through `kubectl port-forward`.
- Terraform uses local state; an S3 backend with locking is still required for
  shared use.
- RDS is single-AZ and the VPC has one NAT gateway; both are development
  defaults.
- The AWS stack is running and billing approximately **$0.22/hour** plus data.

## Next Best Step

Practice against `http://localhost:18080/docs`, then run `terraform destroy`
and confirm EKS, EC2, NAT, and RDS are gone. If a public URL is required, add a
`LoadBalancer` Service or an Ingress; that creates an ELB/ALB and adds cost.

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
