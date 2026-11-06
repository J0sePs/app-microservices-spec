# Proposal

## Why

`withdrawal-soles` currently records and reports PEN withdrawals but never
debits the customer's wallet. The wallet is the only owner of the balance, so a
withdrawal can complete without the money leaving the wallet. The wallet team
published `openapi-billetera.yaml` and `PARA-INTEGRAR-RETIROS.md`; this change
connects the service to that contract.

## What Changes

- Add a `WalletServicePort` and an HTTP adapter for the wallet API:
  `GET /v1/wallets?idUsuario`, `POST /v1/wallets/{walletId}/payments`, and
  `POST /v1/movements/{movementId}/reverse`.
- Sign the wallet JWT (HS256, issuer `billetera-dev`, subject `retiros`,
  60-second lifetime).
- Extend `user-service` ownership with the integer `id_usuario`; a withdrawal
  MUST NOT proceed without it.
- Debit the wallet before reporting and persist `wallet_user_id`, `wallet_id`,
  `wallet_movement_id`, `wallet_reversal_movement_id`, and timestamps.
- Map wallet failures to the agreed withdrawal errors (`WALLET_NOT_FOUND`,
  `INSUFFICIENT_BALANCE`, `USER_INACTIVE`, `WALLET_CONFLICT`,
  `WALLET_AUTH_FAILED`, `DEPENDENCY_UNAVAILABLE`) and guarantee that a failed
  debit creates no withdrawal.
- Add `POST /api/v1/withdrawals/{id}/reverse` and the `REVERSED` status.
- Add a local wallet simulator, adapter tests, API tests, and an end-to-end
  simulation script that can run against the simulator or the published wallet.

## Capabilities

### New Capabilities

- `pen-wallet-integration`: wallet identity, debit, reversal, persistence, and
  error mapping between `withdrawal-soles` and the PEN wallet.

### Modified Capabilities

- `withdrawal-soles`: creation now debits the wallet and exposes reversal and
  wallet identifiers.

## Impact

- New wallet client, settings, domain port, exceptions, model fields, and
  Alembic migration.
- New `POST /api/v1/withdrawals/{id}/reverse` endpoint and new response fields.
- New runtime dependency on `pyjwt` and on the wallet API.
- No change to `user-service`, `transaction-service`, or the wallet codebase.
