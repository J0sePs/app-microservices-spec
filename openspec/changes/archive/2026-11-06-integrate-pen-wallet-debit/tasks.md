# Tasks

## 1. Contract and domain

- [x] 1.1 Add wallet settings (URL, timeout, JWT issuer, subject, secret, TTL) and verify `Settings` loads defaults.
- [x] 1.2 Add wallet value objects, exceptions, and the `WalletServicePort`; verify the domain imports without FastAPI or SQLAlchemy.
- [x] 1.3 Add `id_usuario` to `AccountOwnership` and parse it in the user-service adapter; verify adapter tests cover present and missing values.
- [x] 1.4 Add `amount_to_cents` and verify `250.00` becomes `25000`.

## 2. Wallet adapter

- [x] 2.1 Implement the JWT signer and `GET /v1/wallets?idUsuario`; verify `respx` tests cover success and `404`.
- [x] 2.2 Implement `POST /v1/wallets/{walletId}/payments` with integer cents, external reference, and idempotency; verify success, `409`, `422`, `503`, and timeout mapping.
- [x] 2.3 Implement `POST /v1/movements/{movementId}/reverse`; verify success, already-reversed, and unavailable mapping.

## 3. Persistence and flow

- [x] 3.1 Add wallet columns and the `REVERSED` status to the model, mappers, and repository; verify repository tests round-trip the wallet fields.
- [x] 3.2 Add the Alembic migration and verify `alembic upgrade head` on PostgreSQL.
- [x] 3.3 Debit the wallet in `CreateWithdrawalUseCase`; verify API tests prove balance movement, no movement on failure, and replay safety.
- [x] 3.4 Add `ReverseWithdrawalUseCase` and `POST /api/v1/withdrawals/{id}/reverse`; verify the full-amount reversal, `422` on a second reversal, and `409` without a debit.

## 4. Simulation and verification

- [x] 4.1 Extend `tools/mock_dependencies.py` with the wallet endpoints and seed users 15, 16, 17, and 18; verify the compose stack routes `/v1/` to the mock.
- [x] 4.2 Add `scripts/simulate_wallet_integration.py`; verify it passes in simulator mode and against the published wallet.
- [x] 4.3 Regenerate `openapi.yaml`, update service documentation and the ERD, and verify `make openapi` and `openspec validate --all --strict`.
- [x] 4.4 Run `make verify` and `./init.sh`, record evidence in `feature_list.json`, `progress.md`, and `session-handoff.md`.

## Workflow follow-up

- Archive the change after review and update `openspec/specs/` through the archive command.
