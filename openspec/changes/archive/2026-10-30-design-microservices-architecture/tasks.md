# Tasks

## 1. Architecture index and service catalog

- [x] 1.1 Create `openspec/architecture/README.md` with relative links to the context, catalog, system diagram, every ERD, and the integration contract; verify every target file exists.
- [x] 1.2 Create `openspec/architecture/service-catalog.md` with all six services, responsibility, owned database, and API surface; verify the six names from `context.md` appear exactly once.

## 2. System context diagram

- [x] 2.1 Create `openspec/architecture/system-context.md` with a mermaid flowchart showing clients, Traefik, six services, and six databases; verify it renders and every cataloged service and database appears once.
- [x] 2.2 Document the two primary request paths (withdrawal and reporting) in the same file and verify each path names the gateway, caller, callee, and owned database.

## 3. Per-service ERDs

- [x] 3.1 Create `openspec/architecture/erd/user-service.md` with a mermaid `erDiagram` for `users` and `accounts`, including primary keys, foreign keys, and constraints; verify `erDiagram` and at least one key and constraint are present.
- [x] 3.2 Create `openspec/architecture/erd/deposit-soles.md` with `erDiagram` for PEN deposits and idempotency records; verify primary key, external `account_id`, and a check constraint on amount.
- [x] 3.3 Create `openspec/architecture/erd/deposit-dollars.md` with the USD equivalent of 3.2; verify the currency column is constrained to `USD`.
- [x] 3.4 Create `openspec/architecture/erd/withdrawal-soles.md` with `erDiagram` for PEN withdrawals, status history, idempotency, and reporting attempts; verify primary key, status constraint, and external references are labeled.
- [x] 3.5 Create `openspec/architecture/erd/withdrawal-dollars.md` with the USD equivalent of 3.4; verify the currency column is constrained to `USD`.
- [x] 3.6 Create `openspec/architecture/erd/transaction-service.md` with `erDiagram` for the unified ledger; verify a uniqueness constraint on source service plus source operation identifier.

## 4. Integration contract

- [x] 4.1 Create `openspec/architecture/integration-contract.md` documenting gateway-only HTTP, `X-User-Id`, `Idempotency-Key`, `/api/v1`, the error envelope, and the reporting call; verify each rule matches `specs/service-integration/spec.md`.
- [x] 4.2 Add the withdrawal-to-transaction report schema and the user-ownership validation call to the contract; verify both include method, path, required headers, success response, and error responses.

## 5. Verification and handoff

- [x] 5.1 Run `openspec validate design-microservices-architecture --strict` and `./init.sh`; verify both pass.
- [x] 5.2 Update `feature_list.json` evidence, `progress.md`, and `session-handoff.md`; verify `node scripts/validate-harness.mjs` reports 5/5 subsystems.

## Workflow follow-up

- Archive the change after review and update `openspec/specs/` through the archive command.
