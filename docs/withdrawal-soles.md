# withdrawal-soles

PEN withdrawal microservice for the banking platform. It follows the hexagonal
layout and owns `withdrawal_soles_db`.

## Responsibilities

- Create PEN withdrawals with `S/ 10.00` minimum, `S/ 5,000.00` maximum, and a
  `S/ 10,000.00` daily accumulated limit per account.
- Validate account ownership, currency, and status through `user-service`.
- Enforce `Idempotency-Key` on mutations.
- Persist an auditable lifecycle, idempotency records, and reporting attempts.
- Report approved operations to `transaction-service`.

## Layout

```text
src/withdrawal_soles/
├── api/              FastAPI schemas, routes, dependencies, error handlers
├── application/      Use cases, DTOs, response serializers
├── core/             Settings
├── domain/           Entities, enums, rules, exceptions, ports
└── infrastructure/   SQLAlchemy, HTTP clients, clock
migrations/           Alembic environment and versions
tests/                Unit, application, API, adapter, repository tests
tools/                Local dependency stubs (not production)
```

## Local setup

```bash
make install       # create .venv and install the service + dev tools
make test          # run pytest
make lint          # run ruff
make verify        # ruff + pytest
make run           # uvicorn on http://localhost:8000
```

The health endpoint is `GET /health`. With the compose stack, the interactive
API documentation is at `http://localhost:8080/docs`.

## Configuration

Settings use the `WITHDRAWAL_SOLES_` prefix. See `.env.example`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `WITHDRAWAL_SOLES_DATABASE_URL` | `postgresql+asyncpg://withdrawal:withdrawal@localhost:5432/withdrawal_soles_db` | Owned database |
| `WITHDRAWAL_SOLES_USER_SERVICE_URL` | `http://localhost:8080` | Gateway base URL for user-service |
| `WITHDRAWAL_SOLES_TRANSACTION_SERVICE_URL` | `http://localhost:8080` | Gateway base URL for transaction-service |
| `WITHDRAWAL_SOLES_BUSINESS_TIMEZONE` | `America/Lima` | Daily limit window |
| `WITHDRAWAL_SOLES_HTTP_MAX_ATTEMPTS` | `3` | Outbound retry bound |

## Database migrations

```bash
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1
```

The initial migration creates `withdrawal_operations`,
`withdrawal_status_history`, `idempotency_records`, and `reporting_attempts`.

## Docker Compose

The compose stack includes PostgreSQL 15, the service, Traefik, and local stubs
for the two external services. PostgreSQL is published on host port `55432` to
avoid clashing with a local installation.

```bash
docker compose up --build
```

For a host-run service against the compose database, copy `.env.example` to
`.env` and run `.venv/bin/alembic upgrade head`.

The gateway is at `http://localhost:8080`; the Traefik dashboard is at
`http://localhost:8081`. The service applies migrations before starting.

## API examples

```bash
curl -i -X POST http://localhost:8080/api/v1/withdrawals \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f" \
  -H "Idempotency-Key: demo-1" \
  -d '{"account_id":"1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11","amount":"250.00"}'
```

```bash
curl http://localhost:8080/api/v1/withdrawals/<id> \
  -H "X-User-Id: 9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f"
```

```bash
curl -X POST http://localhost:8080/api/v1/withdrawals/<id>/cancel \
  -H "X-User-Id: 9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f" \
  -H "Idempotency-Key: cancel-1"
```

```bash
curl -X POST http://localhost:8080/api/v1/withdrawals/<id>/report \
  -H "X-User-Id: 9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f" \
  -H "Idempotency-Key: report-1"
```

### OpenAPI contract

The generated contract is checked in at [`openapi.yaml`](../openapi.yaml). It
matches the running FastAPI app, including required headers and error
responses. Regenerate it after changing routes or schemas:

```bash
make openapi
```

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/withdrawals` | Create, validate, approve, report |
| `GET` | `/api/v1/withdrawals` | List owned operations |
| `GET` | `/api/v1/withdrawals/{id}` | Read one owned operation |
| `POST` | `/api/v1/withdrawals/{id}/cancel` | Cancel a `PENDING` operation |
| `POST` | `/api/v1/withdrawals/{id}/report` | Retry ledger reporting |
| `GET` | `/health` | Database readiness |

### Error envelope

```json
{
  "code": "DAILY_LIMIT_EXCEEDED",
  "message": "The daily withdrawal limit was exceeded.",
  "details": {"accumulated": "9900.00", "requested": "200.00", "limit": "10000.00"}
}
```

Common codes: `UNAUTHORIZED`, `MISSING_IDEMPOTENCY_KEY`, `INVALID_AMOUNT`,
`DAILY_LIMIT_EXCEEDED`, `ACCOUNT_NOT_OWNED`, `ACCOUNT_NOT_FOUND`,
`ACCOUNT_NOT_ELIGIBLE`, `IDEMPOTENCY_CONFLICT`, `IDEMPOTENCY_IN_PROGRESS`,
`WITHDRAWAL_NOT_FOUND`, `INVALID_STATE`, `DEPENDENCY_UNAVAILABLE`, and
`REPORTING_FAILED`.

## Architecture references

- `openspec/architecture/system-context.md`
- `openspec/architecture/erd/withdrawal-soles.md`
- `openspec/architecture/integration-contract.md`
