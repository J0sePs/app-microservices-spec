# withdrawal-soles ERD

**Owned database:** `withdrawal_soles_db`

```mermaid
erDiagram
    WITHDRAWAL_OPERATIONS ||--o{ WITHDRAWAL_STATUS_HISTORY : has
    WITHDRAWAL_OPERATIONS ||--o{ REPORTING_ATTEMPTS : retries
    WITHDRAWAL_OPERATIONS ||--|| IDEMPOTENCY_RECORDS : keyed_by

    WITHDRAWAL_OPERATIONS {
        uuid id PK
        uuid account_id "external ref: user_db.accounts.id"
        numeric amount "10.00 to 5000.00"
        string currency "PEN"
        string status "PENDING, APPROVED, REJECTED, COMPLETED, or FAILED"
        timestamp created_at
        timestamp updated_at
    }

    WITHDRAWAL_STATUS_HISTORY {
        uuid id PK
        uuid withdrawal_id FK
        string from_status
        string to_status
        string reason
        timestamp created_at
    }

    IDEMPOTENCY_RECORDS {
        uuid id PK
        string idempotency_key UK "unique key"
        string request_hash
        uuid withdrawal_id FK
        jsonb response_snapshot
        timestamp created_at
    }

    REPORTING_ATTEMPTS {
        uuid id PK
        uuid withdrawal_id FK
        int attempt_number
        string status "PENDING, SENT, or FAILED"
        string transaction_id "external ref: transaction_db.transactions.id"
        string error_message
        timestamp created_at
    }
```

## Constraints

- `withdrawal_operations.amount` must be between `10.00` and `5000.00` PEN.
- `withdrawal_operations.currency` is restricted to `PEN`.
- `withdrawal_operations.status` is restricted to `PENDING`, `APPROVED`,
  `REJECTED`, `COMPLETED`, or `FAILED`.
- `withdrawal_status_history` and `reporting_attempts` reference
  `withdrawal_operations.id` inside the same database.
- `reporting_attempts` has a unique constraint on
  `(withdrawal_id, attempt_number)`.
- `idempotency_records.idempotency_key` is unique.
- `withdrawal_operations.account_id` is an external reference to
  `user_db.accounts.id`.
- `reporting_attempts.transaction_id` is an external reference to
  `transaction_db.transactions.id`.

## Status lifecycle

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> APPROVED
    PENDING --> REJECTED
    APPROVED --> COMPLETED
    APPROVED --> FAILED
    REJECTED --> [*]
    COMPLETED --> [*]
    FAILED --> [*]
```

The daily accumulated limit of `S/ 10,000.00` is enforced with a per-account
aggregate over completed and approved withdrawals for the current day.
