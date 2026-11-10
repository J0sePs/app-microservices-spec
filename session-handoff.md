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
- The AWS practice stack is **destroyed**. The 2026-11-06 teardown removed the
  platform, the infra module (41 resources), the ECR image, and the EKS log
  group; both Terraform states are empty and no billable resources remain.
- The local Docker Compose stack was rebuilt and is running and healthy;
  `localhost:8080` serves the API through Traefik and the HTTP contract check
  passes 11/11.

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

- The AWS environment is down, so the gateway-based checks are unverified until
  the stack is re-applied and the image is redeployed.
- The development JWT secret (`dev-only-change-me`, 18 bytes) is shared by all
  services. Production must inject a strong secret in every deployment.
- The real users-service URL is not published. `WITHDRAWAL_SOLES_USERS_SERVICE_URL`
  is empty locally and falls back to the user-service base URL; when users
  publishes, set it explicitly.
- Terraform uses local state; an S3 backend with locking is required for shared
  use.

## Next Best Step

1. Use the running local stack to test the JWT and users contract:

   ```bash
   .venv/bin/python scripts/wallet_contract_check.py \
     --base-url http://localhost:8080 \
     --wallet-url http://localhost:8080
   ```

2. Redeploy AWS only when the gateway is needed:

   ```bash
   terraform -chdir=infra/terraform apply
   ./scripts/deploy-eks-demo.sh
   ```

3. Stop AWS charges after any practice run:

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
