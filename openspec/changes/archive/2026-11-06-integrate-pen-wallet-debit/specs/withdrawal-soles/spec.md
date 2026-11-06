# Spec Delta

## MODIFIED Requirements

### Requirement: Create a PEN withdrawal

The service SHALL expose `POST /api/v1/withdrawals` accepting `account_id` and
`amount`. It MUST require `X-User-Id` and `Idempotency-Key`, fix the currency to
`PEN`, debit the PEN wallet for the exact amount in integer cents, persist the
operation with the wallet identifiers, and return `201` with the operation
representation. A failed wallet debit MUST prevent the operation from being
persisted.

#### Scenario: Valid request

- **WHEN** an authenticated client submits a valid account and an amount within limits with a new idempotency key
- **THEN** the service debits the wallet, persists one PEN operation with `wallet_id` and `wallet_movement_id`, and returns `201` with its identifier and status

#### Scenario: Wallet debit fails

- **WHEN** the wallet rejects the debit or is unavailable
- **THEN** the service returns the mapped wallet error and creates no operation

#### Scenario: Missing identity

- **WHEN** the request has no `X-User-Id`
- **THEN** the service returns `401` and creates no operation

#### Scenario: Missing idempotency key

- **WHEN** the request has no `Idempotency-Key`
- **THEN** the service returns `422` and creates no operation

### Requirement: Withdrawal lifecycle is auditable

A withdrawal SHALL use only `PENDING`, `APPROVED`, `REJECTED`, `COMPLETED`,
`FAILED`, and `REVERSED`. Every transition MUST be persisted with its previous
status, new status, reason, and timestamp.

#### Scenario: Successful approval

- **WHEN** validation, the wallet debit, and reporting succeed
- **THEN** the recorded transitions are `PENDING -> APPROVED -> COMPLETED` and the wallet identifiers are stored

#### Scenario: Reporting failure

- **WHEN** reporting fails after approval and a successful debit
- **THEN** the operation remains `APPROVED` with the debit intact and the failed attempt is recorded

#### Scenario: Reversal

- **WHEN** the owner reverses an `APPROVED` or `COMPLETED` operation
- **THEN** the operation becomes `REVERSED` and the transition is recorded

#### Scenario: Invalid transition

- **WHEN** an operation in `COMPLETED` is asked to transition to `PENDING`
- **THEN** the service returns `409` with code `INVALID_STATE`
