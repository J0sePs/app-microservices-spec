# Proposal

## Why

Operators and load balancers need a cheap, stable way to confirm that the
service is running and ready to receive traffic. Without it, deployments rely
on manual checks and failures are discovered by users.

## What Changes

- Add `GET /health` that returns the service status.
- Return `200` with a JSON body when the service is ready.
- Return `503` with a JSON body when a required dependency is unavailable.
- Keep the endpoint unauthenticated and cheap to call.

## Capabilities

### New Capabilities

- `service-health`: exposes a read-only health signal for operators and
  infrastructure probes.

### Modified Capabilities

- None.

## Impact

- New HTTP route and handler.
- New response schema.
- No database migration.
- No breaking changes.
