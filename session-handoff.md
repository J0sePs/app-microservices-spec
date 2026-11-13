# Session Handoff

## Verified Now

- `arch-001`, `withdrawal-001`, `infra-001`, `platform-001`, `wallet-001`, and
  `security-001` are `passing` with evidence.
- `./init.sh` passes with 5/5 harness subsystems and 16/16 checks (106 tests).
- **The AWS practice stack is deployed and live** (2026-11-13):
  - `infra/terraform`: 41 resources in `us-east-1` (VPC, NAT, EKS
    `app-nube-2-dev-eks` v1.35.9 with 2 `t3.small` nodes Ready, ECR, private RDS
    PostgreSQL 15.17).
  - `infra/platform`: 10 resources (Traefik 42.2.0 2/2, app 2/2, mock 1/1,
    migration Job Completed, Ingress, public Classic LoadBalancer).
  - Gateway: `http://abc44d73ea94740738c53880a3469936-1565234038.us-east-1.elb.amazonaws.com`
  - `/health`, `/docs`, `/openapi.json`, `/`: 200.
  - `scripts/wallet_contract_check.py` against the gateway: 11/11 checks; debit
    25000 → 24000 cents and reversal restored 25000.
  - Limits through the gateway: `9.99`/`5000.01` → 422 `INVALID_AMOUNT`,
    `10.00` → 201, missing `Idempotency-Key` → 422; operation
    `b2d17e3f-9569-4330-95f0-3af67444150a` reversed (200 `REVERSED`).
  - The local Docker Compose stack is also running and healthy; `localhost:8080`
    serves the API through Traefik.

## Changed This Session

- `scripts/deploy-eks-demo.sh` accepts an optional `WALLET_SERVICE_URL`
  override; it is passed to the platform module as `wallet_service_url`.
- `infra/terraform/README.md` and `infra/platform/README.md` document that
  override.
- `progress.md`, `feature_list.json`, and `session-handoff.md` record the
  deployment.

## Broken Or Unverified

- The stack is **billable** while it runs (~$157/month, ~$0.22/hour).
- The published wallet `http://52.67.162.209` is unreachable (TCP timeout on
  port 80). The deployed service therefore points at the in-cluster
  `mock-dependencies` wallet stub; the repo default still targets the published
  API.
- The gateway is public and has no edge authentication; the service trusts
  `X-User-Id`, so it is practice-only.
- The development JWT secret (`dev-only-change-me`, 18 bytes) is shared by all
  services. Production must inject a strong secret in every deployment.
- The real users-service URL is not published; the deployment uses the
  in-cluster mock through the gateway.
- The code on `feature/cicd-eks-deploy` moves both roots to an S3 backend, but
  the live stack still has **local** state. Before the next apply:
  `./scripts/bootstrap-tf-state.sh`, export `TF_STATE_BUCKET`, then
  `./scripts/tf-init.sh terraform -migrate-state` and
  `./scripts/tf-init.sh platform -migrate-state`.
- `cicd-001` is `in_progress`: no CI deploy has run yet; `actionlint` not run.
- The `billetera` namespace does not exist in the cluster yet; deploys need
  `WALLET_MOCK_ENABLED=1` (script) or the GitHub variable
  `WALLET_MOCK_ENABLED=true`.

## Next Best Step

0. CI/CD (`cicd-001`): merge the `feature/cicd-eks-deploy` PR after
   registering the GitHub secrets (`AWS_ACCESS_KEY_ID`,
   `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `DB_PASSWORD`, `JWT_SECRET`) and
   variables (`TF_STATE_BUCKET`, `EKS_DEPLOY_ENABLED`, `WALLET_MOCK_ENABLED`),
   then confirm the first deploy and archive `cicd-eks-deploy`.

1. When the practice run ends, stop billing:

   ```bash
   ./scripts/destroy-eks-demo.sh
   ```

2. Verify the account is clean afterwards:

   ```bash
   terraform -chdir=infra/terraform state list
   terraform -chdir=infra/platform state list
   aws eks list-clusters --region us-east-1
   aws rds describe-db-instances --region us-east-1 --query 'DBInstances[].DBInstanceIdentifier'
   ```

3. When the published wallet is reachable again, redeploy without the override
   (or set `WALLET_SERVICE_URL=http://52.67.162.209`) and re-run:

   ```bash
   .venv/bin/python scripts/wallet_contract_check.py \
     --base-url http://<gateway> --wallet-url http://52.67.162.209
   ```

4. Send `api/openapi.yaml` to the wallet team.

## Commands

```bash
./init.sh
make verify
make openapi
openspec validate --all --strict

# Wallet and auth simulation
.venv/bin/python scripts/simulate_wallet_integration.py --mode simulate
.venv/bin/python scripts/simulate_wallet_integration.py --mode live

# HTTP contract check against a running service
.venv/bin/python scripts/wallet_contract_check.py --base-url http://localhost:8080 --wallet-url http://localhost:8080
.venv/bin/python scripts/wallet_contract_check.py --base-url http://<gateway> --wallet-url http://<gateway>

# Local stack
docker compose up -d --build
curl http://localhost:8080/health
curl http://localhost:8080/docs

# AWS deployment
terraform -chdir=infra/terraform apply
export TF_STATE_BUCKET=<bucket> AWS_REGION=us-east-1
JWT_SECRET='<shared-with-billetera-api>' WALLET_MOCK_ENABLED=1 ./scripts/deploy-eks-demo.sh
terraform -chdir=infra/platform output -raw gateway_url
kubectl -n withdrawal-soles get pods,svc,ingress

# AWS teardown
./scripts/destroy-eks-demo.sh
```
