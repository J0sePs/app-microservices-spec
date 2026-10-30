# Spec Delta

## Purpose

Establishes database-per-service ownership so each microservice evolves its
schema independently without coupling to another service's storage.

## ADDED Requirements

### Requirement: Each service owns exactly one database

Every microservice SHALL use its own PostgreSQL 15 database: `user_db`,
`deposit_soles_db`, `deposit_dollars_db`, `withdrawal_soles_db`,
`withdrawal_dollars_db`, and `transaction_db`. A service MUST NOT read or write
another service's database.

#### Scenario: Cross-service access is rejected

- **WHEN** `withdrawal-soles` attempts to query `user_db` or `transaction_db`
- **THEN** the access is treated as an architecture violation and the service fails the review

#### Scenario: Database credentials are scoped

- **WHEN** a service is deployed
- **THEN** its credentials grant access only to its owned database

### Requirement: Schema and migrations are service-owned

Each service SHALL own its schema definitions and Alembic migrations. No shared
schema, shared migration history, or shared table MUST exist between services.

#### Scenario: Migration scope

- **WHEN** `withdrawal-soles` runs its migrations
- **THEN** only tables in `withdrawal_soles_db` are created or altered

#### Scenario: Independent evolution

- **WHEN** one service adds a column
- **THEN** no other service requires a coordinated migration

### Requirement: Cross-service references use identifiers, not foreign keys

A service SHALL store identifiers from other domains as plain values and MUST
NOT declare database foreign keys that cross a service boundary.

#### Scenario: Account reference

- **WHEN** `withdrawal-soles` stores `account_id`
- **THEN** the value is validated through `user-service` and no foreign key to `user_db` exists

#### Scenario: Transaction reference

- **WHEN** a completed withdrawal is reported
- **THEN** `transaction-service` owns the transaction record and `withdrawal-soles` keeps only its local operation state

### Requirement: Consistency is coordinated through APIs

Services SHALL avoid distributed transactions and MUST coordinate consistency
through HTTP calls, explicit operation states, and idempotent retries.

#### Scenario: Reporting failure

- **WHEN** `transaction-service` is unavailable after an approved withdrawal
- **THEN** the withdrawal remains in a retryable state and the report is retried without creating a duplicate

#### Scenario: Duplicate delivery

- **WHEN** the same transaction report is delivered twice
- **THEN** `transaction-service` stores one transaction for the operation

### Requirement: Ownership is visible in every ERD

Each service ERD SHALL state the owned database and MUST mark cross-service
identifiers as external references rather than foreign keys.

#### Scenario: ERD review

- **WHEN** a reviewer checks a service ERD
- **THEN** the database name is declared and every cross-service identifier is labeled as an external reference
