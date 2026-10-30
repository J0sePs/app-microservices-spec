# deposit-dollars ERD

**Owned database:** `deposit_dollars_db`

```mermaid
erDiagram
    DEPOSIT_OPERATIONS ||--|| IDEMPOTENCY_RECORDS : keyed_by

    DEPOSIT_OPERATIONS {
        uuid id PK
        uuid account_id "external ref: user_db.accounts.id"
        numeric amount "greater than zero"
        string currency "USD"
        string status "PENDING, COMPLETED, or FAILED"
        timestamp created_at
        timestamp completed_at
    }

    IDEMPOTENCY_RECORDS {
        uuid id PK
        string idempotency_key UK "unique key"
        string request_hash
        uuid operation_id FK
        jsonb response_snapshot
        timestamp created_at
    }
```

## Constraints

- `deposit_operations.currency` is restricted to `USD`.
- `deposit_operations.amount` must be greater than zero.
- `deposit_operations.status` is restricted to `PENDING`, `COMPLETED`, or
  `FAILED`.
- `idempotency_records.idempotency_key` is unique.
- `idempotency_records.operation_id` references
  `deposit_operations.id` inside the same database.
- `deposit_operations.account_id` is an external reference to
  `user_db.accounts.id`; it is not a database foreign key.

## Notes

This is the USD equivalent of `deposit-soles`. The schemas are intentionally
separate so each currency evolves and scales independently.
