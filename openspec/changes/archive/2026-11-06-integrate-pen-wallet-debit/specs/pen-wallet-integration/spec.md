# Spec Delta

## Purpose

Connects PEN withdrawals to the wallet that owns the customer balance, including
identity resolution, debit, reversal, persistence, and error mapping.

## ADDED Requirements

### Requirement: Wallet identity is resolved from user-service

Before a debit, the service SHALL obtain the integer `id_usuario` from the
`user-service` ownership response. If it is missing, the service MUST NOT call
the wallet and MUST return `503` with code `DEPENDENCY_UNAVAILABLE`.

#### Scenario: Identity present

- **WHEN** ownership returns `id_usuario: 15`, currency `PEN`, and status `ACTIVE`
- **THEN** the service queries the wallet with `idUsuario=15`

#### Scenario: Identity missing

- **WHEN** ownership does not include `id_usuario`
- **THEN** the service returns `503` and creates no withdrawal or wallet movement

### Requirement: The wallet is debited before completion

The service SHALL call `GET /v1/wallets?idUsuario` and then
`POST /v1/wallets/{walletId}/payments` with `amount` in integer cents, the
withdrawal UUID as `externalReference`, and the withdrawal UUID as
`Idempotency-Key`. The wallet movement id MUST be stored as
`wallet_movement_id` before the operation is reported and completed.

#### Scenario: Successful debit

- **WHEN** the wallet has enough balance and accepts the payment
- **THEN** the withdrawal stores `wallet_user_id`, `wallet_id`, and
  `wallet_movement_id`, and responds `201`

#### Scenario: Insufficient balance

- **WHEN** the wallet balance is lower than the amount in cents
- **THEN** the service returns `422 INSUFFICIENT_BALANCE` and creates no withdrawal

#### Scenario: Wallet not found

- **WHEN** the wallet responds `404` for the user
- **THEN** the service returns `404 WALLET_NOT_FOUND` and creates no withdrawal

#### Scenario: Wallet unavailable

- **WHEN** the wallet times out or returns an unexpected `5xx`
- **THEN** the service returns `503 DEPENDENCY_UNAVAILABLE` and creates no withdrawal

#### Scenario: Replay

- **WHEN** the same withdrawal `Idempotency-Key` and body are replayed
- **THEN** the service returns the stored withdrawal with `200` and does not debit again

### Requirement: Wallet authentication uses the agreed JWT

Every wallet call SHALL carry `Authorization: Bearer <jwt>` signed with HS256,
issuer `billetera-dev`, subject `retiros`, secret `dev-only-change-me`, and a
lifetime of 60 seconds.

#### Scenario: Valid token

- **WHEN** the service calls the wallet
- **THEN** the token validates with the agreed issuer and secret

### Requirement: Debited withdrawals can be reversed

The service SHALL expose `POST /api/v1/withdrawals/{id}/reverse` accepting a
`reason` of 1 to 500 characters. It MUST call
`POST /v1/movements/{movementId}/reverse` with the key
`<withdrawal-id>:reverse`, store the returned reversal movement, and move the
operation to `REVERSED`. A second reversal MUST return `422`.

#### Scenario: Reverse a completed withdrawal

- **WHEN** the owner reverses a withdrawal that has a `wallet_movement_id`
- **THEN** the wallet is credited the full amount and the withdrawal becomes `REVERSED`

#### Scenario: Reverse without a debit

- **WHEN** the withdrawal has no `wallet_movement_id`
- **THEN** the service returns `409 INVALID_STATE` and calls no wallet endpoint

#### Scenario: Second reversal

- **WHEN** the owner reverses an already reversed withdrawal
- **THEN** the service returns `422 WALLET_ALREADY_REVERSED`

### Requirement: Wallet state is persisted and observable

The service SHALL store `wallet_user_id`, `wallet_id`, `wallet_movement_id`,
`wallet_reversal_movement_id`, `wallet_debited_at`, and `wallet_reversed_at`,
and SHALL expose the wallet identifiers in the withdrawal representation.

#### Scenario: Read after debit

- **WHEN** the owner reads a completed withdrawal
- **THEN** the response includes `wallet_id` and `wallet_movement_id`

### Requirement: The wallet contract is simulatable

The repository SHALL provide a local wallet simulator with the same paths and
payloads, and a script that runs the real use cases against the simulator or
the published wallet.

#### Scenario: Simulator run

- **WHEN** the simulation script runs in simulator mode
- **THEN** debit, insufficient balance, missing wallet, dependency failure, and
  reversal scenarios pass without external network access

#### Scenario: Live run

- **WHEN** the simulation script runs against the published wallet with a
  `S/ 10.00` withdrawal
- **THEN** the wallet balance drops by `1000` cents and returns to the initial
  balance after the reversal
