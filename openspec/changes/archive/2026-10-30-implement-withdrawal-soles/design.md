# Design

## Context

See `proposal.md` for motivation and
`specs/withdrawal-soles/spec.md` for requirements. The platform architecture is
already documented in `openspec/architecture/`; this change implements only the
PEN withdrawal service.

The service is greenfield. It must run against PostgreSQL 15, call
`user-service` and `transaction-service` through Traefik, and stay within the
`withdrawal_soles_db` boundary. The repository uses Python 3.11+.

## Goals / Non-Goals

**Goals:**

- Deliver a runnable, tested FastAPI service with the hexagonal layers named in
  `context.md`.
- Make the domain rules executable and independent of FastAPI and SQLAlchemy.
- Persist an auditable lifecycle, idempotency records, and reporting attempts.
- Make the service verifiable locally and in CI without external services.
- Keep the local stack demonstrable with Docker Compose and Traefik.

**Non-Goals:**

- Implementing `user-service`, `transaction-service`, or any other service.
- Building the AWS infrastructure; Terraform is a separate change.
- Adding an event bus, outbox, or asynchronous worker.
- Implementing an operator approval workflow or a card/ACH network integration.
- Multi-region or high-availability database design.

## Decisions

### 1. Hexagonal layering

Use `domain/` for entities, enums, rules, exceptions, and ports; `application/`
for use cases; `infrastructure/` for SQLAlchemy repositories and HTTP clients;
`api/` for FastAPI schemas, routes, and error mapping; `core/` for settings.
Dependencies point inward: the domain imports no framework, and the application
depends on ports only.

Alternative considered: a conventional `routers/services/models` layout.
Rejected because it couples the rules to FastAPI and makes unit testing depend
on the web layer.

### 2. Immediate approval after validation

A create request is validated, persisted as `PENDING`, and immediately
transitioned to `APPROVED` in the same use case. If the ledger report succeeds,
it transitions to `COMPLETED`; otherwise it stays `APPROVED` for a later retry.

This gives clients a final result for the happy path while preserving the
`PENDING` and `APPROVED` states required by the domain. A future manual review
workflow can stop after `PENDING` without changing the state model.

Alternative considered: leave every request `PENDING` until an operator acts.
Rejected because the project has no approval actor or review API.

### 3. Persist idempotency in PostgreSQL

`idempotency_records` stores the key, a SHA-256 fingerprint of the normalized
request, the operation identifier, and the serialized response. The unique key
constraint is the concurrency boundary. A replay returns the stored response; a
different fingerprint returns `409`.

Alternative considered: an in-memory cache. Rejected because it fails across
restarts and replicas.

### 4. Serialize the daily limit per account

PostgreSQL uses `pg_advisory_xact_lock(hashtext(account_id))` inside the create
transaction. The lock is acquired before summing the day's operations. On
SQLite, used only in tests, the lock is a no-op.

The daily window is computed in `America/Lima` and converted to UTC for
comparison. `PENDING`, `APPROVED`, and `COMPLETED` rows count; `REJECTED` and
`FAILED` do not.

Alternative considered: rely on a unique constraint or a nightly batch. Rejected
because the rule is a cumulative sum, not a uniqueness rule.

### 5. Report synchronously and keep a retry path

After approval, the application calls `transaction-service` with a bounded
timeout and up to three attempts. The withdrawal identifier is the idempotency
key, so retries cannot duplicate the ledger entry. A successful report sets
`COMPLETED` and stores `transaction_id`; a failed report stores a
`reporting_attempts` row and leaves the operation `APPROVED`.

`POST /api/v1/withdrawals/{id}/report` lets the owner retry. It returns `200`
when the operation becomes completed and `202` when the report still fails.

Alternative considered: an outbox worker. Deferred until a broker or background
runtime exists; the persisted attempt table keeps the door open.

### 6. External calls use narrow ports and real timeouts

Define `UserServicePort` and `TransactionServicePort` in the domain. The
infrastructure adapters use `httpx.AsyncClient`, send `X-User-Id`, and map
transport failures to `DependencyUnavailable`. The user call has a 2-second
timeout; the report call has 3 seconds and retries idempotent requests.

Alternative considered: calling `httpx` from use cases directly. Rejected
because it makes the application untestable without network mocks.

### 7. Test with SQLite for speed and PostgreSQL for the migration

API and application tests use an async SQLite file with the same SQLAlchemy
metadata, plus fake ports. This keeps the suite fast and hermetic. The Alembic
migration is verified separately against a PostgreSQL 15 container in the local
compose stack.

The models use portable `Uuid`, `Numeric`, `JSON`, and `DateTime(timezone=True)`
types, with `JSONB` selected only on PostgreSQL.

### 8. Local compose includes dependency stubs

The local compose stack runs PostgreSQL, the service, Traefik, and a small
`mock-dependencies` process that implements the two external contracts. This
makes the full create flow demonstrable without the other services. The mock is
development-only and is not used in tests or production.

## Data model

- `withdrawal_operations`: operation id, `account_id`, `user_id`, amount,
  currency, status, `transaction_id`, timestamps.
- `withdrawal_status_history`: transition audit with previous and new status,
  reason, and timestamp.
- `idempotency_records`: key, request hash, operation id, response snapshot.
- `reporting_attempts`: attempt number, status, transaction id, error message,
  unique per withdrawal and attempt.

The ERD in `openspec/architecture/erd/withdrawal-soles.md` is updated with the
`user_id` ownership column.

## API shape

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/withdrawals` | Create, validate, approve, report |
| `GET` | `/api/v1/withdrawals/{id}` | Read one owned operation |
| `GET` | `/api/v1/withdrawals` | List owned operations with filters |
| `POST` | `/api/v1/withdrawals/{id}/cancel` | Reject a pending operation |
| `POST` | `/api/v1/withdrawals/{id}/report` | Retry ledger reporting |
| `GET` | `/health` | Database readiness |

Amounts are serialized as decimal strings. Errors use the architecture envelope
`{"code", "message", "details"}`.

## Testing strategy

- Domain unit tests: amount bounds, decimal precision, daily limit arithmetic,
  and state transitions.
- Application tests: create success, ownership rejection, daily limit, report
  failure, idempotent replay, cancel, and retry.
- API tests: status codes, headers, error envelope, pagination, and ownership
  isolation using an async SQLite database and fake ports.
- Adapter tests: `respx` for the user and transaction clients, including
  timeouts, retries, and error mapping.
- Migration smoke test: apply Alembic against PostgreSQL 15 in compose.

## Risks / Trade-offs

- [Synchronous report adds latency to create] → Keep the report timeout short
  and allow `APPROVED` responses when the ledger is slow.
- [PostgreSQL advisory locks are database-specific] → Isolate the lock in the
  repository adapter and no-op on SQLite.
- [The local mock can drift from the real contracts] → Keep the mock limited to
  the documented endpoints and cover the real adapters with contract tests.
- [Auto-approval may not match a future manual review process] → The state
  machine already supports `PENDING`; only the transition policy changes.
- [SQLite differs from PostgreSQL] → Use portable types, run the migration
  smoke test on PostgreSQL, and keep PostgreSQL-specific behavior behind
  dialect checks.

## Migration Plan

1. Add the Python project, domain, and tests.
2. Add persistence and the Alembic migration.
3. Add adapters, use cases, API, and error handling.
4. Add Docker Compose, Traefik, and the local dependency stubs.
5. Run lint, tests, `openspec validate`, and `./init.sh`.
6. Update the architecture ERD with `user_id`, then archive the change.

Rollback: stop the containers and drop `withdrawal_soles_db`; no other service
or database is affected.
