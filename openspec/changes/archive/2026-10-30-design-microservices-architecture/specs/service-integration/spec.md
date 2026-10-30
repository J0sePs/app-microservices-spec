# Spec Delta

## Purpose

Defines how independent services communicate securely and reliably through the
API gateway, including identity forwarding, idempotent mutations, and reporting.

## ADDED Requirements

### Requirement: Traefik is the only service entry point

All external and inter-service HTTP traffic SHALL pass through Traefik v3.
Services MUST NOT be called directly by clients or by other services in a
deployed environment.

#### Scenario: External request

- **WHEN** a client calls a banking API
- **THEN** the request reaches the target service through Traefik route rules

#### Scenario: Service-to-service request

- **WHEN** `withdrawal-soles` calls `user-service`
- **THEN** the call uses the gateway base URL and not a direct container or pod address

### Requirement: Identity is delegated to the gateway

Traefik SHALL validate the JWT and forward the authenticated subject as
`X-User-Id` and the caller role as `X-User-Role`. Services MUST reject requests
without `X-User-Id` and MUST NOT trust client-supplied identity headers.

#### Scenario: Authenticated request

- **WHEN** a valid JWT reaches the gateway
- **THEN** the downstream request carries `X-User-Id` and the service processes it

#### Scenario: Missing identity

- **WHEN** a request without `X-User-Id` reaches a service
- **THEN** the service responds with `401` and creates no operation

### Requirement: Mutations require an idempotency key

Every mutating endpoint SHALL require an `Idempotency-Key` header. A replay with
the same key and the same request body MUST return the original result without
creating a second operation.

#### Scenario: First submission

- **WHEN** a client submits a withdrawal with a new `Idempotency-Key`
- **THEN** one withdrawal operation is created and its identifier is returned

#### Scenario: Replay

- **WHEN** the client repeats the request with the same key and body
- **THEN** the original operation is returned with the same identifier and no duplicate is persisted

#### Scenario: Key reuse with different body

- **WHEN** a client reuses an `Idempotency-Key` with a different payload
- **THEN** the service responds with `409` and does not modify the original operation

### Requirement: Service contracts use versioned HTTP APIs

Service APIs SHALL use JSON over HTTP under `/api/v1`, publish request and
response schemas, and return a consistent error envelope with a machine-readable
code.

#### Scenario: Validation error

- **WHEN** a request violates the contract
- **THEN** the service returns a `4xx` response with `code`, `message`, and `details` fields

#### Scenario: Contract discovery

- **WHEN** a consumer reads the integration contract
- **THEN** the endpoint, method, required headers, success response, and error responses are documented

### Requirement: Approved withdrawals are reported to transaction-service

`withdrawal-soles` SHALL report every `APPROVED` or `COMPLETED` withdrawal to
`transaction-service` over HTTP with an idempotent operation reference.
Reporting failures MUST NOT silently discard the operation.

#### Scenario: Successful report

- **WHEN** a withdrawal reaches `APPROVED`
- **THEN** `withdrawal-soles` sends a report and records the transaction identifier

#### Scenario: Reporting outage

- **WHEN** `transaction-service` is unavailable
- **THEN** the withdrawal is marked for retry and remains queryable

#### Scenario: Duplicate report

- **WHEN** the same withdrawal is reported twice
- **THEN** `transaction-service` keeps one transaction for that withdrawal reference

### Requirement: Remote calls are bounded

Every outbound HTTP call SHALL define a timeout and MUST NOT exceed three retry
attempts for idempotent operations. A timed-out mutation MUST be reconciled by
operation status before retrying.

#### Scenario: User-service timeout

- **WHEN** `user-service` does not answer within the configured timeout
- **THEN** the withdrawal is rejected or left pending according to the documented failure policy, and no unverified approval is issued

#### Scenario: Retry bound

- **WHEN** a dependency keeps failing
- **THEN** the service stops after three attempts and records a failure state
