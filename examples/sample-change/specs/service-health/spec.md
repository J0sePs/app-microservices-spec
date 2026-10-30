# Spec Delta

## Purpose

Provides a stable, machine-readable signal that the service is alive and ready
to serve traffic.

## ADDED Requirements

### Requirement: Health endpoint reports readiness

The service SHALL expose `GET /health` and return a JSON body with a `status`
field. The endpoint MUST be available without authentication.

#### Scenario: Service is ready

- **WHEN** a client sends `GET /health` and required dependencies are available
- **THEN** the service responds with `200` and `{"status":"ok"}`

#### Scenario: Service is not ready

- **WHEN** a client sends `GET /health` and a required dependency is unavailable
- **THEN** the service responds with `503` and `{"status":"unavailable"}`

### Requirement: Health endpoint stays cheap

The health endpoint SHALL NOT perform expensive work or mutate state.

#### Scenario: Repeated probes

- **WHEN** a client sends ten `GET /health` requests in one second
- **THEN** every response completes without writing to the database or filesystem
