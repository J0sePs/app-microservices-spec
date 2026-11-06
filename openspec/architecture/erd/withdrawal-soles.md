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
        uuid user_id "external ref: user_db.users.id"
        int wallet_user_id "external ref: wallet idUsuario"
        uuid wallet_id "external ref: wallet wallets.id"
        uuid wallet_movement_id "external ref: wallet movements.id"
        uuid wallet_reversal_movement_id "external ref: wallet movements.id"
        numeric amount "10.00 to 5000.00"
        string currency "PEN"
        string status "PENDING, APPROVED, REJECTED, COMPLETED, REVERSED, or FAILED"
        timestamp wallet_debited_at
        timestamp wallet_reversed_at
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
  `REJECTED`, `COMPLETED`, `REVERSED`, or `FAILED`.
- `withdrawal_operations.wallet_user_id`, `wallet_id`, `wallet_movement_id`, and
  `wallet_reversal_movement_id` are external references to the PEN wallet and
  are stored as values, not database foreign keys.
- `withdrawal_status_history` and `reporting_attempts` reference
  `withdrawal_operations.id` inside the same database.
- `reporting_attempts` has a unique constraint on
  `(withdrawal_id, attempt_number)`.
- `idempotency_records.idempotency_key` is unique.
- `withdrawal_operations.account_id` is an external reference to
  `user_db.accounts.id`.
- `withdrawal_operations.user_id` is an external reference to
  `user_db.users.id`; it stores the authenticated owner for read isolation.
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
    APPROVED --> REVERSED
    COMPLETED --> REVERSED
    REJECTED --> [*]
    COMPLETED --> [*]
    FAILED --> [*]
    REVERSED --> [*]
```

The daily accumulated limit of `S/ 10,000.00` is enforced with a per-account
aggregate over completed and approved withdrawals for the current day.
