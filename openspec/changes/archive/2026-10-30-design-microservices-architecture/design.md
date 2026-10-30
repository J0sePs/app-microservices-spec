# Design

## Context

See `proposal.md` for motivation. The repository currently contains the project
brief (`context.md`) and the harness. No service code or architecture documents
exist yet. This design defines the baseline that later changes implement:
`withdrawal-soles` first, then the AWS cluster.

Constraints from `context.md`:

- Six services, one per domain-currency slice, plus shared `user-service` and
  `transaction-service`.
- Python 3.11+, FastAPI, PostgreSQL 15, SQLAlchemy 2.0 async, Alembic.
- Traefik v3 as the single entry point.
- One database per service; no cross-service database access.
- JWT authentication delegated to the gateway, with `X-User-Id` forwarding.
- Idempotency required on mutations.

## Goals / Non-Goals

**Goals:**

- Establish one authoritative catalog of services, responsibilities, databases,
  and API surfaces.
- Make the end-to-end request path visible in a single system-context diagram.
- Give every service an ERD before implementation starts, so schema ownership
  and cross-service references are explicit.
- Define integration rules that the `withdrawal-soles` implementation must obey.
- Keep the documentation renderable in GitHub and consumable by agents.

**Non-Goals:**

- Writing application code for any service.
- Provisioning AWS infrastructure or Terraform modules.
- Defining internal class structure for services other than the constraints
  needed by `withdrawal-soles`.
- Choosing a production service mesh, message broker, or event bus.

## Decisions

### 1. Split services by domain and currency

Use `deposit-soles`, `deposit-dollars`, `withdrawal-soles`, and
`withdrawal-dollars` rather than one deposit service and one withdrawal service.
Currency-specific services isolate regulatory rules, limits, and failure
domains, and let each currency scale independently.

Alternative considered: one service per domain with a currency parameter.
Rejected because it couples deployment and schema changes across currencies and
weakens the database-per-service boundary.

### 2. Use one PostgreSQL database per service

Each service gets its own logical database and credentials. Cross-service
identifiers (`account_id`, `transaction_id`, `user_id`) are stored as plain
values and validated through APIs, never via cross-database foreign keys.

Alternative considered: a shared `banking_db` schema. Rejected because it
reintroduces a shared schema, coordinated migrations, and a single failure
domain.

### 3. Keep synchronous HTTP for the first version

The platform uses synchronous HTTP through Traefik. `withdrawal-soles` calls
`user-service` to validate account ownership and `transaction-service` to report
approved operations. Reliability comes from timeouts, bounded retries,
idempotency keys, and explicit operation states.

Alternative considered: an event bus with outbox delivery. Deferred because the
project has no broker requirement yet and synchronous reporting is sufficient
for the first delivery. The operation-state design leaves room to add an outbox
later.

### 4. Delegate authentication to Traefik

Traefik validates JWTs and forwards `X-User-Id` and `X-User-Role`. Services
trust only those headers and reject requests that lack them. This keeps token
parsing out of every service and gives one place to change the identity
provider.

Alternative considered: each service validates JWTs. Rejected because it
duplicates security code and multiplies key-rotation work.

### 5. Make idempotency a storage concern

Mutating endpoints require `Idempotency-Key`. The owning service persists the
key, a request fingerprint, and the resulting resource identifier in its own
database. Replays return the stored result; key reuse with a different body
returns `409`.

Alternative considered: in-memory idempotency cache. Rejected because it does
not survive restarts or multiple replicas.

### 6. Treat documentation as code

Architecture documents live in `openspec/architecture/` and use mermaid so they
render on GitHub and stay reviewable in pull requests. The architecture index is
the entry point; every diagram has a relative link. The documents are part of
the definition of done for this change.

Alternative considered: a wiki or external diagramming tool. Rejected because
it drifts from the repository and is not visible to agents.

### 7. Local Docker Compose, target AWS EKS

Local development uses Docker Compose with PostgreSQL containers and Traefik.
The target environment is an AWS EKS cluster with Traefik as ingress and
PostgreSQL as a managed dependency. Terraform for the cluster is a separate
change after this architecture baseline.

## Data model baseline

- `user_db`: `users`, `accounts`.
- `deposit_soles_db` and `deposit_dollars_db`: deposit operations, one
  idempotency record per mutation.
- `withdrawal_soles_db` and `withdrawal_dollars_db`: withdrawal operations,
  status history, idempotency records, reporting attempts.
- `transaction_db`: unified transaction ledger keyed by source service and
  source operation identifier.

Cross-service fields are stored as identifiers only. ERDs mark them as external
references.

## API conventions

- Base path: `/api/v1`.
- JSON request and response bodies.
- Identity: `X-User-Id` header injected by the gateway.
- Mutations: `Idempotency-Key` header required.
- Errors: `{"code": "...", "message": "...", "details": {...}}`.
- Health: `GET /health` returns process and dependency readiness.
- Withdrawal lifecycle: `PENDING -> APPROVED -> COMPLETED`, or
  `PENDING -> REJECTED`, or `APPROVED -> FAILED`.

## Migration Plan

1. Write the architecture index, catalog, system diagram, ERDs, and integration
   contract.
2. Validate the OpenSpec artifacts and the harness.
3. Archive this change to publish the durable specs.
4. Use the archived specs as the input for `implement-withdrawal-soles`.

Rollback is documentation-only: revert the commit that adds
`openspec/architecture/`. No runtime state is affected.

## Risks / Trade-offs

- [Documentation drifts from implementation] → Require architecture updates in
  the definition of done for every service change, and keep diagram paths in the
  index.
- [Traefik becomes a single point of failure] → Run at least two replicas in
  the target cluster and keep health checks in the gateway configuration.
- [Synchronous reporting couples availability] → Persist reporting attempts,
  retry idempotently, and expose a retryable state instead of dropping reports.
- [Six small services increase operational overhead] → Share the same tech
  stack, container conventions, and CI template across services.
