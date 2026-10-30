# transaction-service ERD

**Owned database:** `transaction_db`

```mermaid
erDiagram
    TRANSACTIONS ||--o{ TRANSACTION_EVENTS : has

    TRANSACTIONS {
        uuid id PK
        string source_service "unique with source_operation_id"
        string source_operation_id "unique with source_service"
        uuid account_id "external ref: user_db.accounts.id"
        string type "DEPOSIT or WITHDRAWAL"
        numeric amount "greater than zero"
        string currency "PEN or USD"
        string status "POSTED or REVERSED"
        timestamp occurred_at
        timestamp created_at
    }

    TRANSACTION_EVENTS {
        uuid id PK
        uuid transaction_id FK
        string event_type
        jsonb payload
        timestamp created_at
    }
```

## Constraints

- `transactions` has a unique constraint on
  `(source_service, source_operation_id)`, making reporting idempotent.
- `transactions.type` is restricted to `DEPOSIT` or `WITHDRAWAL`.
- `transactions.currency` is restricted to `PEN` or `USD`.
- `transactions.amount` must be greater than zero.
- `transactions.status` is restricted to `POSTED` or `REVERSED`.
- `transaction_events.transaction_id` references `transactions.id` inside the
  same database.
- `transactions.account_id` is an external reference to
  `user_db.accounts.id`.

## Notes

The unique source pair is the idempotency boundary: replaying the same report
updates nothing and returns the existing transaction identifier.
