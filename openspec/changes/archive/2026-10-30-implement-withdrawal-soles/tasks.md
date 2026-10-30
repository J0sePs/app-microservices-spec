# Tasks

## 1. Project scaffolding and tooling

- [x] 1.1 Create `pyproject.toml`, the `src/withdrawal_soles/` package skeleton, and Python ignore rules; verify `pip install -e ".[dev]"` succeeds in `.venv` and `python -c "import withdrawal_soles"` works.
- [x] 1.2 Add a `Makefile` with install, lint, test, run, migrate, and verify targets; verify `make verify` runs lint and tests.
- [x] 1.3 Update `init.sh`, `scripts/verify.sh`, and `.github/workflows/verify.yml` to install Python dependencies and run pytest in CI; verify `./init.sh` executes the Python verification step.
- [x] 1.4 Add `tests/conftest.py` with async SQLite fixtures, fake ports, and a fixed clock; verify `pytest --collect-only` succeeds.

## 2. Domain layer

- [x] 2.1 Implement status enums, domain entities, and domain exceptions; verify unit tests assert the five withdrawal statuses and exception codes.
- [x] 2.2 Implement amount and daily-limit rules with `Decimal`; verify unit tests cover `9.99`, `10.00`, `5000.00`, `5000.01`, three decimal places, and the `10000.00` boundary.
- [x] 2.3 Define repository, user-service, transaction-service, clock, and identifier ports; verify the domain package imports without FastAPI or SQLAlchemy.

## 3. Persistence and migrations

- [x] 3.1 Implement SQLAlchemy models for operations, status history, idempotency records, and reporting attempts with keys, indexes, and check constraints; verify `Base.metadata.create_all` succeeds on SQLite.
- [x] 3.2 Implement async settings, engine, session factory, and dependency-friendly session handling; verify a test connects and executes `SELECT 1`.
- [x] 3.3 Implement the SQLAlchemy repository with create, get, list, daily sum, advisory lock, idempotency, status history, and reporting attempt methods; verify repository tests pass.
- [x] 3.4 Add the Alembic configuration and initial migration with all four tables; verify `alembic upgrade head` against the compose PostgreSQL instance and inspect the created tables.

## 4. External service adapters

- [x] 4.1 Implement the `user-service` ownership client with `X-User-Id`, a 2-second timeout, retries, and error mapping; verify `respx` tests cover success, `403`, `404`, timeout, and `5xx`.
- [x] 4.2 Implement the `transaction-service` report client with a 3-second timeout, bounded retries, and ledger idempotency; verify `respx` tests cover success, retry then success, `409`, and timeout.

## 5. Application use cases

- [x] 5.1 Implement `CreateWithdrawalUseCase` with ownership validation, daily limit, lifecycle transitions, idempotency, and reporting; verify application tests cover success, rejection, report failure, and replay.
- [x] 5.2 Implement get, list, cancel, and retry-report use cases with ownership isolation and state rules; verify tests cover owner/non-owner reads, cancel transitions, and report retry outcomes.

## 6. HTTP API

- [x] 6.1 Implement Pydantic request/response schemas, dependency wiring, lifespan clients, and the domain-error handler; verify schema serialization tests and the error envelope.
- [x] 6.2 Implement the withdrawal routes for create, get, list, cancel, and report; verify API tests cover `201`, `200`, `202`, `401`, `403`, `404`, `409`, and `422`.
- [x] 6.3 Implement `GET /health` with a database probe; verify `200` when reachable and `503` when the session fails.

## 7. Runtime and documentation

- [x] 7.1 Add the `Dockerfile`, `docker-compose.yml` with PostgreSQL, Traefik, the service, and local dependency stubs, plus `.env.example`; verify `docker compose config` and a container build succeed.
- [x] 7.2 Write the service README with setup, migrations, API examples, and compose instructions; verify every documented command runs as written.
- [x] 7.3 Update `openspec/architecture/erd/withdrawal-soles.md` with the `user_id` ownership column and the retry-report endpoint in the integration contract; verify links and `erDiagram` remain valid.

## 8. Verification and handoff

- [x] 8.1 Run the full suite: `make verify`, `openspec validate implement-withdrawal-soles --strict`, and `./init.sh`; verify all pass.
- [x] 8.2 Update `feature_list.json` with evidence, and update `progress.md` and `session-handoff.md`; verify `node scripts/validate-harness.mjs` reports 5/5 subsystems.
- [x] 8.3 Record the final test count and coverage of the specified scenarios in the feature evidence; verify the evidence names the executed commands.

## Workflow follow-up

- Archive the change after review and update `openspec/specs/` through the archive command.
