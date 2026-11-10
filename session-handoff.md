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
- The AWS practice stack is **destroyed** (2026-11-10):
  - `./scripts/destroy-eks-demo.sh` destroyed `infra/platform` (9 resources)
    and `infra/terraform` (41 resources); both Terraform states are empty.
  - No EKS, RDS, ECR, VPC, NAT, ELB, EBS, or EKS log group remains in
    `us-east-1`. The remaining EIP `32.199.142.201` is tagged
    `machupicchu-eip` and unrelated.
- The published Billetera Digital PEN API v1.1.0
  (`http://52.67.162.209`) was consumed end to end through the AWS gateway
  before teardown:
  - Contract check: 11/11.
  - Withdrawal `74e2f8e7-a36e-417d-b781-1af20d15ada9`: payment debit
    `7bc4cef5-9a05-49af-8bc0-f51eb3d6a325`, reversal credit
    `849ab4e0-3120-48cf-b839-eb09e0e00826`, balance `25000 -> 24000 -> 25000`
    cents.
- The local Docker Compose stack is also running and healthy; `localhost:8080`
  serves the API through Traefik.

## Changed This Session

- `postman/withdrawal-soles-billetera.postman_collection.json` tests both
  services (withdrawal-soles and Billetera PEN) plus an integrated flow; the
  collection signs the service JWT automatically.
- `README.md` now documents only `withdrawal-soles`: responsibilities, domain
  rules, HTTP contract, local commands, and the `withdrawal_soles_db` ERD with
  its constraints and status lifecycle.
- The repository is published to `J0sePs/app-microservices-spec`; `origin/main`
  includes the full local history after an `--allow-unrelated-histories` merge.
- The generated contract now lives at `api/openapi.yaml`; `make openapi` writes
  there. It reflects 7 operations, `BearerAuth`, the current gateway URL, and
  the published wallet dependency.
- `api/openapi-service2.yaml` is checked in as the reference contract for the
  consumed wallet API.
- The wallet base URL moved to `http://52.67.162.209` in settings,
  `.env.example`, docs, scripts, and the platform module
  (`wallet_service_url` variable, default the published API).
- The EKS deployment now sets `WITHDRAWAL_SOLES_WALLET_SERVICE_URL` from that
  variable instead of the in-cluster mock.

## Broken Or Unverified

- The AWS practice stack is torn down; redeploy it only for a practice run and
  destroy it again afterwards (~$157/month while it runs).
- The published wallet is an external dependency; its availability gates
  withdrawals.
- The gateway is public and has no edge authentication; the service trusts
  `X-User-Id`, so it is practice-only.
- The development JWT secret (`dev-only-change-me`, 18 bytes) is shared by all
  services. Production must inject a strong secret in every deployment.
- The real users-service URL is not published. `WITHDRAWAL_SOLES_USERS_SERVICE_URL`
  is empty and falls back to the user-service base URL; when users publishes,
  set it explicitly.
- Terraform uses local state; an S3 backend with locking is required for shared
  use.

## Next Best Step

1. Send `api/openapi.yaml` to the wallet team.
2. Re-run the integration when the published wallet changes:

   ```bash
   .venv/bin/python scripts/wallet_contract_check.py \
     --base-url http://<gateway> \
     --wallet-url http://52.67.162.209
   ```

3. Redeploy AWS only when needed, then stop charges afterwards:

   ```bash
   terraform -chdir=infra/terraform apply
   ./scripts/deploy-eks-demo.sh
   # ... practice ...
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
.venv/bin/python scripts/wallet_contract_check.py --base-url http://<gateway> --wallet-url http://52.67.162.209

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
