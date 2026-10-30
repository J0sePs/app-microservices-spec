# Proposal

## Why

The architecture baseline is documented, but the repository still has no
runtime service. Clients need a working PEN withdrawal service that enforces the
bank's limits, validates account ownership, persists an auditable lifecycle, and
reports approved operations to the transaction ledger.

## What Changes

- Add a FastAPI service using the hexagonal layout: `api/`, `application/`,
  `domain/`, `infrastructure/`, and `core/`.
- Add `POST /api/v1/withdrawals`, `GET /api/v1/withdrawals/{id}`,
  `GET /api/v1/withdrawals`, `POST /api/v1/withdrawals/{id}/cancel`,
  `POST /api/v1/withdrawals/{id}/report`, and `GET /health`.
- Enforce PEN-only operations, `S/ 10.00` minimum, `S/ 5,000.00` maximum, and a
  `S/ 10,000.00` daily accumulated limit per account.
- Require `X-User-Id` and `Idempotency-Key`; persist idempotency records so
  replays return the original result.
- Validate account ownership, currency, and status through `user-service` over
  HTTP through Traefik.
- Report approved operations to `transaction-service` with a retryable
  reporting record.
- Add PostgreSQL 15 tables, SQLAlchemy async repositories, and Alembic
  migrations for `withdrawal_soles_db`.
- Add unit, application, API, and HTTP-client tests, plus Docker Compose with
  Traefik and local dependency stubs.
- Update the verification gate and CI to install Python dependencies and run
  lint and tests.

## Capabilities

### New Capabilities

- `withdrawal-soles`: PEN withdrawal creation, limits, ownership validation,
  lifecycle, idempotency, reporting, reads, cancellation, and health.

### Modified Capabilities

- None.

## Impact

- New `src/withdrawal_soles/`, `tests/`, `migrations/`, `Dockerfile`,
  `docker-compose.yml`, `pyproject.toml`, and service documentation.
- Changes to `init.sh`, `scripts/verify.sh`, and the GitHub Actions workflow to
  support Python verification.
- New runtime dependency on PostgreSQL, `user-service`, and
  `transaction-service`.
- No changes to the other five services and no Terraform resources.
