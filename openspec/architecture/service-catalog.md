# Service Catalog

| Service | Responsibility | Owned database | API surface |
| --- | --- | --- | --- |
| `user-service` | Customer identity and bank account ownership | `user_db` | `GET /api/v1/accounts/{account_id}`, `GET /api/v1/accounts/{account_id}/ownership` |
| `deposit-soles` | Deposit operations in PEN | `deposit_soles_db` | `POST /api/v1/deposits`, `GET /api/v1/deposits/{id}` |
| `deposit-dollars` | Deposit operations in USD | `deposit_dollars_db` | `POST /api/v1/deposits`, `GET /api/v1/deposits/{id}` |
| `withdrawal-soles` | Withdrawal operations in PEN | `withdrawal_soles_db` | `POST /api/v1/withdrawals`, `GET /api/v1/withdrawals`, `GET /api/v1/withdrawals/{id}`, `POST /api/v1/withdrawals/{id}/cancel`, `POST /api/v1/withdrawals/{id}/report` |
| `withdrawal-dollars` | Withdrawal operations in USD | `withdrawal_dollars_db` | `POST /api/v1/withdrawals`, `GET /api/v1/withdrawals/{id}`, `POST /api/v1/withdrawals/{id}/cancel` |
| `transaction-service` | Unified transaction ledger | `transaction_db` | `POST /api/v1/transactions`, `GET /api/v1/transactions/{id}` |

## Boundaries

- Each deposit and withdrawal service handles exactly one domain and one
  currency. A PEN request must never be processed by a USD service.
- `user-service` owns customers and accounts for both currencies.
- `transaction-service` owns the unified ledger and is the only service that
  stores cross-domain transaction history.
- A service stores identifiers from other domains as values, never as database
  foreign keys.

## Shared platform components

| Component | Responsibility |
| --- | --- |
| Traefik v3 | Single HTTP entry point, routing, JWT validation, identity headers |
| PostgreSQL 15 | One logical database per service |
| Alembic | Per-service schema migrations |
| Docker Compose | Local development topology |
| AWS EKS | Target cluster topology |
