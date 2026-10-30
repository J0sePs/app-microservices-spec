# Design

## Context

The service already has an HTTP router and a dependency client. See
`proposal.md` for motivation.

## Goals / Non-Goals

**Goals:**

- Add a read-only health route.
- Distinguish "process alive" from "ready to serve traffic".
- Keep the handler independent of business logic.

**Non-Goals:**

- Deep dependency diagnostics.
- Metrics or tracing changes.
- Authentication for the endpoint.

## Decisions

- **Use `GET /health` instead of `/healthz`.** `GET /health` is the project's
  existing convention and is easy to document. `/healthz` was considered but
  rejected for consistency.
- **Return a JSON body.** Infrastructure can ignore it, while operators get a
  readable status. A plain `200` was considered but gives less signal.
- **Check only required dependencies.** Optional services should not make the
  service unready.

## Risks / Trade-offs

- [The health check becomes a hidden dependency check] → Keep the check cheap
  and limit it to required dependencies.
- [Probes create load] → Cache the dependency status for a short window if
  measurements show a problem.
