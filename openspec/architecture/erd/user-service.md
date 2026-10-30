# user-service ERD

**Owned database:** `user_db`

```mermaid
erDiagram
    USERS ||--o{ ACCOUNTS : owns

    USERS {
        uuid id PK
        string document_number UK "unique identity document"
        string full_name
        string email UK "unique email"
        timestamp created_at
        timestamp updated_at
    }

    ACCOUNTS {
        uuid id PK
        uuid user_id FK
        string account_number UK "unique account number"
        string currency "PEN or USD"
        numeric balance "non-negative"
        string status "ACTIVE, BLOCKED, or CLOSED"
        timestamp created_at
        timestamp updated_at
    }
```

## Constraints

- `users.document_number` and `users.email` are unique.
- `accounts.account_number` is unique.
- `accounts.currency` is restricted to `PEN` or `USD`.
- `accounts.status` is restricted to `ACTIVE`, `BLOCKED`, or `CLOSED`.
- `accounts.balance` must be greater than or equal to zero.
- `accounts.user_id` references `users.id` inside the same database.

## Notes

This service owns customer and account data. Other services reference
`accounts.id` as an external value and must validate it through the
`user-service` API.
