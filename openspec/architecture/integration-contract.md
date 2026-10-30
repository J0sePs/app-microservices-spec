# Integration Contract

All communication is JSON over HTTP under `/api/v1`. Traefik is the only entry
point; deployed services are never called directly.

## Common rules

| Rule | Value |
| --- | --- |
| Gateway | Traefik v3 |
| Identity header | `X-User-Id` (injected by Traefik) |
| Role header | `X-User-Role` (injected by Traefik) |
| Idempotency header | `Idempotency-Key` (required on every mutation) |
| Content type | `application/json` |
| User request timeout | 2 seconds |
| Transaction report timeout | 3 seconds |
| Retry bound | 3 attempts with exponential backoff |

Missing `X-User-Id` returns `401`. Services must ignore any identity header
supplied directly by a client; only gateway-injected values are trusted.

## Error envelope

```json
{
  "code": "WITHDRAWAL_LIMIT_EXCEEDED",
  "message": "The daily withdrawal limit was exceeded.",
  "details": {
    "limit": "10000.00",
    "accumulated": "9500.00",
    "requested": "1000.00"
  }
}
```

| Status | Meaning |
| --- | --- |
| `400` | Malformed request |
| `401` | Missing or invalid identity |
| `403` | Authenticated but not allowed |
| `404` | Resource not found |
| `409` | Idempotency conflict or invalid state transition |
| `422` | Domain validation failure |
| `503` | Required dependency unavailable |

## withdrawal-soles

### Create a withdrawal

`POST /api/v1/withdrawals`

Required headers: `X-User-Id`, `Idempotency-Key`, `Content-Type`.

```json
{
  "account_id": "1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11",
  "amount": "250.00"
}
```

The service fixes `currency` to `PEN`. A first submission returns `201`; a
replay with the same key and body returns `200` with the same body. The create
response is `COMPLETED` when the ledger accepts the report and `APPROVED` when
reporting must be retried.

```json
{
  "id": "6f1d3a4b-8c2e-4a9f-b7d1-2e5c8a0f9b33",
  "account_id": "1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11",
  "amount": "250.00",
  "currency": "PEN",
  "status": "PENDING",
  "created_at": "2026-10-30T12:00:00Z"
}
```

Errors: `401` missing identity, `409` key reused with a different body, `422`
amount outside `10.00`–`5000.00`, daily limit exceeded, non-PEN account, or
inactive account.

### Get a withdrawal

`GET /api/v1/withdrawals/{id}`

Required headers: `X-User-Id`. Returns the same representation as the create
response. Returns `404` when the operation does not exist or does not belong to
the caller.

### Cancel a withdrawal

`POST /api/v1/withdrawals/{id}/cancel`

Required headers: `X-User-Id`, `Idempotency-Key`, `Content-Type`.

Only `PENDING` operations can be cancelled. Returns `200` with status
`REJECTED`; an already cancelled operation returns the same result. A
non-pending operation returns `409`.

### Retry reporting

`POST /api/v1/withdrawals/{id}/report`

Required headers: `X-User-Id`, `Idempotency-Key`. Only the owner can retry an
`APPROVED` operation. Returns `200` with `COMPLETED` when the ledger accepts the
report, or `202` with `APPROVED` when the report still fails. A completed
operation returns `200` unchanged; any other status returns `409`.

### Health

`GET /health`

Returns `200` with `{"status":"ok"}` when the service and database are ready,
and `503` with `{"status":"unavailable"}` otherwise. No authentication.

## user-service: ownership validation

`GET /api/v1/accounts/{account_id}/ownership`

Required headers: `X-User-Id`. Called by deposit and withdrawal services through
the gateway. The response tells the caller whether the account belongs to the
authenticated user, its currency, and whether it can operate.

```json
{
  "account_id": "1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11",
  "owner_user_id": "9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f",
  "currency": "PEN",
  "status": "ACTIVE",
  "owned": true
}
```

Errors: `401` missing identity, `403` account belongs to another user, `404`
account not found.

## transaction-service: operation report

`POST /api/v1/transactions`

Required headers: `X-User-Id`, `Idempotency-Key`, `Content-Type`. Withdrawal and
deposit services call this endpoint through the gateway after an operation
reaches a reportable state.

```json
{
  "source_service": "withdrawal-soles",
  "source_operation_id": "6f1d3a4b-8c2e-4a9f-b7d1-2e5c8a0f9b33",
  "account_id": "1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11",
  "type": "WITHDRAWAL",
  "amount": "250.00",
  "currency": "PEN",
  "status": "POSTED",
  "occurred_at": "2026-10-30T12:00:05Z"
}
```

A first report returns `201`; a replay for the same
`(source_service, source_operation_id)` returns `200` with the existing
transaction. A conflicting payload for the same pair returns `409`.

```json
{
  "transaction_id": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
  "source_service": "withdrawal-soles",
  "source_operation_id": "6f1d3a4b-8c2e-4a9f-b7d1-2e5c8a0f9b33",
  "status": "POSTED",
  "created_at": "2026-10-30T12:00:06Z"
}
```

Errors: `401` missing identity, `409` conflicting replay, `422` invalid payload.

## Reporting policy

- `withdrawal-soles` reports when the operation reaches `APPROVED` or
  `COMPLETED`.
- The `Idempotency-Key` equals `source_operation_id`.
- A failed report is persisted in `reporting_attempts` with `FAILED`; the
  operation remains queryable.
- Retries are bounded to three attempts and use exponential backoff.
- A report must never create a second ledger entry for the same source pair.
