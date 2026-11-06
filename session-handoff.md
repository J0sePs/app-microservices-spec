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
- The local Docker Compose stack is running and healthy; `localhost:8080`
  serves the API through Traefik.
- The AWS practice stack is **running and billing** since 2026-11-06 in
  `us-east-1`, account `205346659030`:
  - infra: 41 resources (VPC, EKS `app-nube-2-dev-eks` v1.35, 2 × `t3.small`
    nodes Ready, ECR, RDS PostgreSQL 15).
  - platform: 10 resources (Traefik 42.2.0 2/2, app 2/2, mock 1/1, migration
    Job Completed, Ingress).
  - Gateway: `http://a6c1a4b5ffa8a44808f8a8a0784fe0d7-266125410.us-east-1.elb.amazonaws.com`
  - The deployed image predates the JWT and users changes; redeploy before
    testing through the gateway.

## Changed This Session

- Added mandatory inbound service JWT validation and kept `X-User-Id` as the
  end-user identity.
- Added `GET /usuarios/{idUsuario}` validation before debit and reversal, with
  `USER_NOT_FOUND`, `USER_INACTIVE`, and `DEPENDENCY_UNAVAILABLE` mapping.
- Extended the mock and simulator with JWT verification and the users stub.
- Added `scripts/wallet_contract_check.py` and `make contract-check` for a
  teammate to verify a running service over HTTP.
- Regenerated `openapi.yaml` with the `BearerAuth` scheme and updated the
  integration documents.
- Archived `secure-api-jwt-users-contract` as
  `2026-11-06-secure-api-jwt-users-contract`; the main specs now include
  `service-authentication`.

## Broken Or Unverified

- The AWS practice stack costs about $0.22/hour (~$5.20/day) and must be
  destroyed when practice ends.
- The deployed EKS image predates these changes. Run
  `./scripts/deploy-eks-demo.sh` before testing JWT and the users contract
  through the gateway.
- The development JWT secret (`dev-only-change-me`, 18 bytes) is shared by all
  services. Production must inject a strong secret in every deployment.
- The real users-service URL is not published. `WITHDRAWAL_SOLES_USERS_SERVICE_URL`
  is empty locally and falls back to the user-service base URL; when users
  publishes, set it explicitly.
- Terraform uses local state; an S3 backend with locking is required for shared
  use.

## Next Best Step

1. Redeploy the new image before testing through the gateway:

   ```bash
   ./scripts/deploy-eks-demo.sh
   ```

2. Run the HTTP check against the gateway:

   ```bash
   .venv/bin/python scripts/wallet_contract_check.py \
     --base-url http://<gateway> \
     --wallet-url http://18.228.136.200
   ```

3. Stop AWS charges when practice ends:

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

# AWS teardown
./scripts/destroy-eks-demo.sh
```
