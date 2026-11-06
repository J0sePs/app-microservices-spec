# Spec Delta

## Purpose

Defines the inbound service authentication that protects every business route of
`withdrawal-soles`.

## ADDED Requirements

### Requirement: Business routes require a service JWT

Every route under `/api/v1/withdrawals` SHALL require
`Authorization: Bearer <jwt>` signed with HS256, issuer `billetera-dev`, the
configured secret, a non-expired `exp`, and an allowed `sub` (default
`retiros`). A missing, malformed, expired, wrong-issuer, or wrong-subject token
MUST return `401` with code `UNAUTHORIZED` and create no operation.

#### Scenario: Valid token

- **WHEN** a caller sends a correctly signed, unexpired token with `sub=retiros`
- **THEN** the service processes the request normally

#### Scenario: Missing token

- **WHEN** a caller sends `X-User-Id` and `Idempotency-Key` but no `Authorization` header
- **THEN** the service returns `401 UNAUTHORIZED` and creates no operation

#### Scenario: Invalid token

- **WHEN** the token uses a different secret, issuer, subject, or is expired
- **THEN** the service returns `401 UNAUTHORIZED` and creates no operation

#### Scenario: Public routes

- **WHEN** a caller requests `/health`, `/`, `/docs`, or `/openapi.json`
- **THEN** the service responds without requiring a token

### Requirement: User identity remains explicit

The service SHALL use `X-User-Id` as the UUID of the end user for ownership,
scoping, and persistence. A valid service token alone MUST NOT be accepted as a
user identity.

#### Scenario: Token without user identity

- **WHEN** a caller sends a valid token but no `X-User-Id`
- **THEN** the service returns `401 UNAUTHORIZED` and creates no operation

#### Scenario: User isolation

- **WHEN** two callers use different `X-User-Id` values with valid tokens
- **THEN** each one reads only its own withdrawals
