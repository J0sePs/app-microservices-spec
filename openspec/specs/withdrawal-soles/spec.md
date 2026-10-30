# withdrawal-soles Specification

## Purpose
Provides PEN withdrawal operations with bank limits, ownership validation,
idempotency, an auditable lifecycle, and reporting to the transaction ledger.

## Requirements

### Requirement: Create a PEN withdrawal

The service SHALL expose `POST /api/v1/withdrawals` accepting `account_id` and
`amount`. It MUST require `X-User-Id` and `Idempotency-Key`, fix the currency to
`PEN`, persist the operation, and return `201` with the operation
representation.

#### Scenario: Valid request

- **WHEN** an authenticated client submits a valid account and an amount within limits with a new idempotency key
- **THEN** the service persists one PEN operation and returns `201` with its identifier and status

#### Scenario: Missing identity

- **WHEN** the request has no `X-User-Id`
- **THEN** the service returns `401` and creates no operation

#### Scenario: Missing idempotency key

- **WHEN** the request has no `Idempotency-Key`
- **THEN** the service returns `422` and creates no operation

### Requirement: Amount limits are enforced

A withdrawal SHALL be at least `S/ 10.00` and at most `S/ 5,000.00`, with no
more than two decimal places. Values outside those bounds MUST be rejected
without persisting an operation.

#### Scenario: Below minimum

- **WHEN** the amount is `9.99` PEN
- **THEN** the service returns `422` with code `INVALID_AMOUNT` and creates no operation

#### Scenario: Above maximum

- **WHEN** the amount is `5000.01` PEN
- **THEN** the service returns `422` with code `INVALID_AMOUNT` and creates no operation

#### Scenario: Boundary values

- **WHEN** the amount is exactly `10.00` or exactly `5000.00` PEN
- **THEN** the service accepts the operation if every other rule passes

#### Scenario: Excess decimal places

- **WHEN** the amount has more than two decimal places
- **THEN** the service returns `422` with code `INVALID_AMOUNT`

### Requirement: Daily accumulated limit is enforced

The service SHALL limit the sum of a single account's `PENDING`, `APPROVED`, and
`COMPLETED` withdrawals to `S/ 10,000.00` per business day in the
`America/Lima` time zone. Requests that would exceed the limit MUST be rejected.

#### Scenario: Limit exceeded

- **WHEN** an account has `S/ 9,900.00` accumulated and requests `S/ 200.00`
- **THEN** the service returns `422` with code `DAILY_LIMIT_EXCEEDED` and creates no operation

#### Scenario: Limit reached exactly

- **WHEN** the projected accumulated total is exactly `S/ 10,000.00`
- **THEN** the service accepts the operation

#### Scenario: Rejected operations do not count

- **WHEN** an operation is `REJECTED` or `FAILED`
- **THEN** its amount is excluded from the daily accumulated total

#### Scenario: Concurrent requests

- **WHEN** two requests for the same account are processed concurrently near the limit
- **THEN** the service serializes them and at most one succeeds

### Requirement: Account ownership is validated

Before approving a withdrawal, the service SHALL call `user-service` through
Traefik to confirm that the account belongs to the caller, uses `PEN`, and is
active. A failed ownership check MUST prevent the operation.

#### Scenario: Ownership confirmed

- **WHEN** `user-service` reports `owned: true`, currency `PEN`, and status `ACTIVE`
- **THEN** the service continues with the withdrawal

#### Scenario: Account belongs to another user

- **WHEN** `user-service` reports `owned: false`
- **THEN** the service returns `403` with code `ACCOUNT_NOT_OWNED` and creates no operation

#### Scenario: Account missing

- **WHEN** `user-service` returns `404`
- **THEN** the service returns `404` with code `ACCOUNT_NOT_FOUND`

#### Scenario: Account not eligible

- **WHEN** the account currency is not `PEN` or its status is not `ACTIVE`
- **THEN** the service returns `422` with code `ACCOUNT_NOT_ELIGIBLE`

#### Scenario: User service unavailable

- **WHEN** `user-service` times out or returns `5xx`
- **THEN** the service returns `503` with code `DEPENDENCY_UNAVAILABLE` and creates no operation

### Requirement: Mutations are idempotent

The service SHALL persist an idempotency record per key and request
fingerprint. Replaying the same key and body MUST return the original result
without creating a second operation. Reusing a key with a different body MUST
return `409`.

#### Scenario: Replay

- **WHEN** the client repeats a create request with the same `Idempotency-Key` and body
- **THEN** the service returns `200` with the original operation and stores no second operation

#### Scenario: Key reuse with different body

- **WHEN** the client reuses a key with a different account or amount
- **THEN** the service returns `409` with code `IDEMPOTENCY_CONFLICT`

#### Scenario: Concurrent duplicate

- **WHEN** two create requests with the same key arrive concurrently
- **THEN** at most one operation is created and the other receives `409` with code `IDEMPOTENCY_IN_PROGRESS` or the original result

### Requirement: Withdrawal lifecycle is auditable

A withdrawal SHALL use only `PENDING`, `APPROVED`, `REJECTED`, `COMPLETED`, and
`FAILED`. Every transition MUST be persisted with its previous status, new
status, reason, and timestamp.

#### Scenario: Successful approval

- **WHEN** validation and reporting succeed
- **THEN** the recorded transitions are `PENDING -> APPROVED -> COMPLETED`

#### Scenario: Reporting failure

- **WHEN** reporting fails after approval
- **THEN** the operation remains `APPROVED` and the failed attempt is recorded

#### Scenario: Invalid transition

- **WHEN** an operation in `COMPLETED` is asked to transition to `PENDING`
- **THEN** the service returns `409` with code `INVALID_STATE`

### Requirement: Pending withdrawals can be cancelled

`POST /api/v1/withdrawals/{id}/cancel` SHALL move a `PENDING` operation to
`REJECTED`. Cancelling an already `REJECTED` operation MUST return the same
result, and any other status MUST return `409`.

#### Scenario: Cancel pending

- **WHEN** the owner cancels a `PENDING` operation
- **THEN** the status becomes `REJECTED` and the transition is recorded

#### Scenario: Repeat cancellation

- **WHEN** the owner cancels an already `REJECTED` operation
- **THEN** the service returns `200` with the same representation

#### Scenario: Cancel approved

- **WHEN** the owner cancels an `APPROVED` operation
- **THEN** the service returns `409` with code `INVALID_STATE`

### Requirement: Approved operations are reported

After reaching `APPROVED`, the service SHALL call `transaction-service`
`POST /api/v1/transactions` with source service `withdrawal-soles`, the
withdrawal identifier as source operation, account, amount, currency `PEN`,
type `WITHDRAWAL`, status `POSTED`, and occurrence time.

#### Scenario: Successful report

- **WHEN** the ledger accepts the report
- **THEN** the withdrawal becomes `COMPLETED` with the returned transaction identifier

#### Scenario: Reporting failure

- **WHEN** the ledger is unavailable
- **THEN** the withdrawal remains `APPROVED`, a `FAILED` reporting attempt is stored, and the create response still returns the operation

#### Scenario: Duplicate report

- **WHEN** the same withdrawal is reported again
- **THEN** `transaction-service` returns the same transaction and no duplicate ledger entry is created

#### Scenario: Retry reporting

- **WHEN** the owner calls `POST /api/v1/withdrawals/{id}/report` for an `APPROVED` operation
- **THEN** the service retries the report and returns `200` when completed or `202` when it remains pending

### Requirement: Withdrawals can be read by their owner

`GET /api/v1/withdrawals/{id}` and `GET /api/v1/withdrawals` SHALL return only
operations owned by the caller. Reads MUST NOT mutate state.

#### Scenario: Owner reads operation

- **WHEN** the owner requests a withdrawal by identifier
- **THEN** the service returns `200` with its current representation

#### Scenario: Different user reads operation

- **WHEN** a different authenticated user requests the same identifier
- **THEN** the service returns `404`

#### Scenario: List filters

- **WHEN** the owner lists withdrawals filtered by account and status
- **THEN** only matching operations owned by that user are returned with pagination metadata

### Requirement: Health reports readiness

`GET /health` SHALL be unauthenticated and return `200` with
`{"status":"ok"}` when the database is reachable, or `503` with
`{"status":"unavailable"}` otherwise.

#### Scenario: Database reachable

- **WHEN** the service can execute a database query
- **THEN** `GET /health` returns `200`

#### Scenario: Database unavailable

- **WHEN** the database connection fails
- **THEN** `GET /health` returns `503`

### Requirement: Persistence is isolated and auditable

All withdrawal data SHALL be stored in `withdrawal_soles_db` using the tables
for operations, status history, idempotency records, and reporting attempts.
The service MUST NOT access another service's database and MUST apply schema
changes through Alembic.

#### Scenario: Database isolation

- **WHEN** the service handles a request
- **THEN** it reads and writes only `withdrawal_soles_db`

#### Scenario: Audit trail

- **WHEN** an operation changes status or reporting is attempted
- **THEN** a corresponding history or reporting row is stored
