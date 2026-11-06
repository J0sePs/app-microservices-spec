# Session Handoff

## Verified Now

- `arch-001`, `withdrawal-001`, `infra-001`, `platform-001`, and `wallet-001`
  are `passing` with evidence.
- `./init.sh` passes with 5/5 harness subsystems and 16/16 checks.
- Wallet integration is verified locally and live:
  - `make verify`: ruff clean, 83 tests passed.
  - Simulator: 12/12 checks passed.
  - Published wallet: 10/10 checks passed; wallet 15 balance was restored to
    25000 cents after the S/ 10.00 debit and reversal.
  - Alembic `0002_add_wallet_integration` applied on PostgreSQL 15.
- The AWS practice stack is **running and billing** since 2026-11-06 in
  `us-east-1`, account `205346659030`:
  - infra: 41 resources (VPC, EKS `app-nube-2-dev-eks` v1.35, 2 × `t3.small`
    nodes Ready, ECR, RDS PostgreSQL 15).
  - platform: 10 resources (Traefik 42.2.0 2/2, app 2/2, mock 1/1, migration
    Job Completed, Ingress).
  - Gateway: `http://a6c1a4b5ffa8a44808f8a8a0784fe0d7-266125410.us-east-1.elb.amazonaws.com`
  - Note: the deployed image predates the wallet integration; redeploy to test
    wallet debit through the gateway.
- The local Docker Compose stack is not running; `localhost:8080` is down. The
  database was started only for the migration check and removed with
  `docker compose down -v`.

## Changed This Session

- Added the `integrate-pen-wallet-debit` change and implemented the wallet
  adapter, debit-in-create, full reversal, `REVERSED` status, migration, and
  wallet columns.
- Added a local wallet simulator and the end-to-end simulation script.
- Regenerated `openapi.yaml` and updated the service docs, ERD, and integration
  contract.
- Recorded evidence in `feature_list.json` and `progress.md`.

## Broken Or Unverified

- The AWS practice stack is up and costs about $0.22/hour (~$5.20/day). It must
  be destroyed when practice ends.
- The public gateway has no authentication; practice-only.
- The deployed EKS image is `df278ed`, which does not include the wallet
  integration. Run `./scripts/deploy-eks-demo.sh` to publish the new code.
- The wallet JWT secret is the agreed development secret (`dev-only-change-me`,
  18 bytes). Production must inject a strong secret.
- Terraform uses local state; an S3 backend with locking is required for shared
  use.
- The change is archived as `2026-11-06-integrate-pen-wallet-debit`; the main
  `pen-wallet-integration` spec exists and `withdrawal-soles` includes
  `REVERSED`.

## Next Best Step

1. Redeploy the new image before testing wallet debit through the gateway:

   ```bash
   ./scripts/deploy-eks-demo.sh
   ```

2. Stop AWS charges when practice ends:

   ```bash
   ./scripts/destroy-eks-demo.sh
   ```

## Commands

```bash
./init.sh
make verify
make openapi
openspec validate --all --strict

# Wallet integration simulation
.venv/bin/python scripts/simulate_wallet_integration.py --mode simulate
.venv/bin/python scripts/simulate_wallet_integration.py --mode live

# Local stack
docker compose up -d --build
curl http://localhost:8080/docs

# AWS deployment
terraform -chdir=infra/terraform apply
./scripts/deploy-eks-demo.sh
terraform -chdir=infra/platform output -raw gateway_url

# AWS teardown
./scripts/destroy-eks-demo.sh
```
