# Proposal

## Why

The platform spans six independently deployable services with strict data
ownership and gateway-only communication. Without a documented architecture
baseline, service boundaries, database ownership, and integration rules drift,
and each new service is built against incompatible assumptions. This change
establishes that baseline before `withdrawal-soles` is implemented.

## What Changes

- Define the service catalog: `user-service`, `deposit-soles`,
  `deposit-dollars`, `withdrawal-soles`, `withdrawal-dollars`, and
  `transaction-service`, including responsibility and owned database.
- Add an authoritative system-context mermaid diagram covering clients,
  Traefik, all services, and their databases.
- Add one mermaid ERD per microservice with tables, keys, and constraints, and
  an index that links every diagram.
- Define data ownership: one PostgreSQL 15 database per service, no shared
  schemas, no direct cross-service database access.
- Define integration rules: HTTP through Traefik, JWT identity delegated to the
  gateway and forwarded as `X-User-Id`, mandatory `Idempotency-Key` on
  mutations, and HTTP reporting to `transaction-service`.
- Document the deployment topology: Docker Compose for local development and
  AWS EKS as the target cluster.
- Keep application code, Terraform, and the other five services out of scope.

## Capabilities

### New Capabilities

- `platform-architecture`: service catalog, domain boundaries, system-context
  diagram, per-service ERDs, and deployment topology.
- `data-ownership`: database-per-service rules, schema ownership, migration
  ownership, and consistency without shared databases.
- `service-integration`: gateway-only HTTP communication, identity forwarding,
  idempotency, error handling, and transaction reporting.

### Modified Capabilities

- None.

## Impact

- New documentation under `openspec/architecture/`.
- New durable specs under `openspec/specs/` after archive.
- No runtime code, database migration, or deployed infrastructure in this
  change.
- Harness subsystems affected: Instructions (architecture reading path), Scope
  (baseline for later changes), and Lifecycle (restart context for agents).
