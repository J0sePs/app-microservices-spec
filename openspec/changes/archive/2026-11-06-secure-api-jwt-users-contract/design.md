# Design

## Context

The published integration document defines one shared development credential:
HS256, issuer `billetera-dev`, secret `dev-only-change-me`. The wallet expects
`sub=retiros` from this service; the wallet itself uses `sub=billetera-service`
when it calls users-service. The token is therefore a **service** identity, not
an end-user identity.

## Goals / Non-Goals

**Goals:**

- Reject anonymous business calls even when `X-User-Id` is present.
- Keep the existing user-scoped API contract and `X-User-Id` semantics.
- Apply the users-service `404` / `422` / `503` mapping before debit and
  reversal.
- Give the teammate a reproducible HTTP checker.

**Non-Goals:**

- Issuing end-user tokens or replacing `X-User-Id` with a token claim.
- Implementing users-service or wallet code.
- Changing amounts, limits, idempotency, or persistence.

## Decisions

### 1. The JWT authenticates the caller; `X-User-Id` identifies the user

The only agreed token carries `sub=retiros` (a service subject). It cannot say
which customer is withdrawing. The service therefore requires both:

- `Authorization: Bearer <jwt>` validated against the configured secret,
  issuer, and an allowed-subject list;
- `X-User-Id`, a UUID, for ownership and row scoping.

Alternative considered: put the user UUID in `sub` and drop `X-User-Id`.
Rejected because it contradicts the agreed token and would break every existing
client. Alternative considered: accept `sub=retiros` **or** a UUID. Rejected as
extra complexity that weakens the documented contract.

### 2. Validation happens on the router, not per route

`include_router(..., dependencies=[Depends(require_service_token)])` protects
all withdrawal operations in one place and keeps `health` and `root` public.
FastAPI documents the scheme through `HTTPBearer`, so `openapi.yaml` is
generated with the security requirement.

### 3. Users-service validation is a separate call with its own token

`UserServiceClient.get_user(id_usuario)` calls
`GET {users_service_url}/usuarios/{idUsuario}` with a token signed as
`billetera-service`, a 2-second timeout, and one attempt. Internal retries are
not used: the documented retry unit is the withdrawal request, replayed with the
same `Idempotency-Key`. `users_service_url` is optional and falls back to
`user_service_url`.

Mapping:

| Users response | Service response |
| --- | --- |
| `200` and `estado is true` | continue |
| `404` or body id mismatch | `404 USER_NOT_FOUND` |
| `200` and `estado` is not `true` | `422 USER_INACTIVE` |
| timeout, `5xx`, or any other status | `503 DEPENDENCY_UNAVAILABLE` |

The create flow validates the `id_usuario` returned by ownership. The reversal
flow validates the stored `wallet_user_id`.

### 4. The mock mirrors the published contract

The local mock verifies the same JWT (issuer, subject, signature) for wallet and
users routes and seeds users 15, 16, and 18 active and 17 inactive. This makes
the simulator exercise the real auth path instead of bypassing it.

### 5. Verification is HTTP-first for the teammate

`scripts/wallet_contract_check.py` talks only to public URLs: it proves `401`
without a token, creates and reverses a withdrawal with the service JWT, and
reads the wallet balance with the wallet JWT. It is safe to rerun because the
amount is reversed.
