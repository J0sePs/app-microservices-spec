# Spec Delta

## ADDED Requirements

### Requirement: Wallet operations validate the user with users-service

Before a debit and before a reversal, the service SHALL call
`GET /usuarios/{idUsuario}` with a service JWT (`sub=billetera-service`,
60-second lifetime) and a 2-second budget. It MUST continue only when the
response is `200`, the body id equals the path id, and `estado` is the boolean
`true`. The body id may be named `idUsuario` or `id_usuario`.

#### Scenario: Active user

- **WHEN** users-service returns `200` with `{"idUsuario": 15, "estado": true}`
- **THEN** the service continues with the wallet call

#### Scenario: Active user with alias

- **WHEN** users-service returns `200` with `{"id_usuario": 15, "estado": true}`
- **THEN** the service accepts the body and continues

### Requirement: Users-service failures block wallet writes

A failed users-service validation MUST map to a stable withdrawal error and MUST
NOT create a withdrawal, movement, or reversal.

#### Scenario: User does not exist

- **WHEN** users-service returns `404` or a different body id
- **THEN** the service returns `404 USER_NOT_FOUND` and writes nothing

#### Scenario: Inactive user

- **WHEN** users-service returns `200` with `estado` equal to `false` or any non-boolean value
- **THEN** the service returns `422 USER_INACTIVE` and writes nothing

#### Scenario: Users-service unavailable

- **WHEN** the users call times out or returns an unexpected status
- **THEN** the service returns `503 DEPENDENCY_UNAVAILABLE` and writes nothing

#### Scenario: Reversal validation

- **WHEN** the owner reverses a debited withdrawal and the user is no longer active
- **THEN** the service returns `422 USER_INACTIVE` and does not credit the wallet

## MODIFIED Requirements

### Requirement: The wallet contract is simulatable

The repository SHALL provide a local simulator that mirrors the published wallet
and users contracts, including JWT verification, and scripts that run the real
use cases against the simulator or the published wallet and check a running
service over HTTP.

#### Scenario: Simulator run

- **WHEN** the simulation script runs in simulator mode
- **THEN** debit, replay, insufficient balance, missing wallet, inactive user, dependency failure, and reversal scenarios pass without external network access

#### Scenario: Live run

- **WHEN** the simulation script runs against the published wallet with a
  `S/ 10.00` withdrawal
- **THEN** the wallet balance drops by `1000` cents and returns to the initial
  balance after the reversal

#### Scenario: HTTP contract check

- **WHEN** the contract checker runs against a running service
- **THEN** it proves `401` without a token, creates and reverses a withdrawal with the service JWT, and reports the resulting wallet balance
