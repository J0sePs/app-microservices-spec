# Spec Delta

## MODIFIED Requirements

### Requirement: Create a PEN withdrawal

The service SHALL expose `POST /api/v1/withdrawals` accepting `account_id` and
`amount`. It MUST require a valid service JWT, `X-User-Id`, and
`Idempotency-Key`, fix the currency to `PEN`, validate the wallet owner with
users-service, debit the PEN wallet for the exact amount in integer cents,
persist the operation with the wallet identifiers, and return `201` with the
operation representation. A failed users or wallet call MUST prevent the
operation from being persisted.

#### Scenario: Valid request

- **WHEN** an authenticated client submits a valid account and an amount within limits with a new idempotency key
- **THEN** the service validates the user, debits the wallet, persists one PEN operation with `wallet_id` and `wallet_movement_id`, and returns `201` with its identifier and status

#### Scenario: Wallet debit fails

- **WHEN** the wallet rejects the debit or is unavailable
- **THEN** the service returns the mapped wallet error and creates no operation

#### Scenario: Missing token

- **WHEN** the request has no valid `Authorization: Bearer` token
- **THEN** the service returns `401` and creates no operation

#### Scenario: Missing identity

- **WHEN** the request has a valid token but no `X-User-Id`
- **THEN** the service returns `401` and creates no operation

#### Scenario: Missing idempotency key

- **WHEN** the request has no `Idempotency-Key`
- **THEN** the service returns `422` and creates no operation
