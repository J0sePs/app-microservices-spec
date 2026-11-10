# Session Handoff

## Verified Now

- `arch-001`, `withdrawal-001`, `infra-001`, `platform-001`, `wallet-001`, and
  `security-001` are `passing` with evidence.
- `./init.sh` passes with 5/5 harness subsystems and 16/16 checks.
- Service authentication and the users contract are verified locally:
  - `make verify`: ruff clean, 106 tests passed.
  - Simulator: 15/15 checks in `simulate`, 9/9 in `live`.
  - HTTP checker against the compose stack: 11/11 checks with the balance
    restored.
  - `openspec validate --all --strict`: 8 passed, 0 failed.
- The AWS practice stack is **up** (Session 018):
  - `infra/terraform`: 41 resources — VPC, NAT, EKS 1.35 with 2 `t3.small`
    nodes, ECR, private RDS PostgreSQL 15 (`db.t4g.micro`), IAM, SGs.
  - `infra/platform`: Traefik gateway, namespace, DB secret, Alembic job, two
    app replicas, mock dependencies, ingress.
  - Gateway: `http://a0f4e669772d6496a9125e3de34cffbc-795710705.us-east-1.elb.amazonaws.com`
  - Contract check through the gateway: 11/11 checks passed.
- The local Docker Compose stack is also running and healthy; `localhost:8080`
  serves the API through Traefik.

## Changed This Session

- `infra/platform/ingress.tf`: added `/usuarios` and `/v1/` prefix routes to
  `mock-dependencies` so the users and wallet mocks are reachable through the
  AWS gateway.
- `infra/platform/app.tf`: added `WITHDRAWAL_SOLES_WALLET_SERVICE_URL` pointing
  at the in-cluster Traefik service. Without it the app used the external
  `18.228.136.200` default and returned `503 DEPENDENCY_UNAVAILABLE`.
- `infra/platform/README.md`: documented the new mock routes and self-contained
  service URLs.

## Broken Or Unverified

- The AWS stack costs roughly $157/month while it runs. Destroy it when the
  practice run ends.
- The gateway is public and has no edge authentication; the service trusts
  `X-User-Id`, so it is practice-only.
- The development JWT secret (`dev-only-change-me`, 18 bytes) is shared by all
  services. Production must inject a strong secret in every deployment.
- The real users-service URL is not published. `WITHDRAWAL_SOLES_USERS_SERVICE_URL`
  is empty locally and falls back to the user-service base URL; when users
  publishes, set it explicitly.
- Terraform uses local state; an S3 backend with locking is required for shared
  use.

## Next Best Step

1. Use the AWS gateway for gateway-based checks:

   ```bash
   terraform -chdir=infra/platform output -raw gateway_url
   .venv/bin/python scripts/wallet_contract_check.py \
     --base-url http://<gateway> \
     --wallet-url http://<gateway>
   ```

2. Stop AWS charges after the practice run:

   ```bash
   ./scripts/destroy-eks-demo.sh
   ```

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

# Local stack
docker compose up -d --build
curl http://localhost:8080/health
curl http://localhost:8080/docs

# AWS deployment
terraform -chdir=infra/terraform apply
./scripts/deploy-eks-demo.sh
terraform -chdir=infra/platform output -raw gateway_url
kubectl -n withdrawal-soles get pods,svc,ingress

# AWS teardown
./scripts/destroy-eks-demo.sh
```
