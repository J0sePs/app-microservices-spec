# Proposal

## Why

`PARA-INTEGRAR-RETIROS-3.md` states that the withdrawal service uses the same
service authentication as the wallet: every business call carries
`Authorization: Bearer <jwt>` (HS256, issuer `billetera-dev`, subject
`retiros`), and `X-User-Id` does not replace that token. Today the service only
trusts `X-User-Id`, so any caller that knows a user UUID can create withdrawals.

The same document publishes the users-service contract
`GET {USERS_SERVICE_URL}/usuarios/{idUsuario}` with a 2-second budget and the
`404` / `422` / `503` mapping the wallet applies before debiting or reversing.
The service does not validate that contract before touching the balance.

## What Changes

- Require a valid service JWT on every business route. Missing, malformed,
  expired, wrong-issuer, or wrong-subject tokens return `401` with the
  `UNAUTHORIZED` code. `/health`, `/docs`, `/openapi.json`, and `/` stay public.
- Keep `X-User-Id` as the end-user identity because the agreed token is a
  service credential (`sub=retiros`); a token without `X-User-Id` still returns
  `401`.
- Verify the wallet owner with `GET /usuarios/{idUsuario}` before a debit and
  before a reversal, signing its own service token (`sub=billetera-service`,
  60-second lifetime) and translating `404`, inactive `estado`, timeout, and
  unexpected statuses to `USER_NOT_FOUND`, `USER_INACTIVE`, and
  `DEPENDENCY_UNAVAILABLE`.
- Add the users stub and JWT verification to the local mock, extend the
  simulator, and add a pure-HTTP contract checker a teammate can run against
  the local stack or the published wallet.
- Regenerate `openapi.yaml` and update the integration documents.

## Capabilities

### New Capabilities

- `service-authentication`: the inbound service JWT contract and its `401`
  behavior.

### Modified Capabilities

- `pen-wallet-integration`: debits and reversals now validate the wallet owner
  with users-service before calling the wallet.
- `withdrawal-soles`: creation requires both the service JWT and `X-User-Id`.

## Impact

- New settings, an auth dependency, a users-service client method, and two
  domain errors.
- No schema migration: the existing wallet columns already identify the user.
- New runtime behavior depends on users-service reachability; a missing URL
  falls back to the configured user-service base URL.
- No change to the wallet, users-service, or transaction-service codebases.
