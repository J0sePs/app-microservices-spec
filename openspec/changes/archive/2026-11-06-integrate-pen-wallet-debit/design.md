# Design

## Context

See `proposal.md` and `specs/pen-wallet-integration/spec.md`. The wallet is the
single owner of the PEN balance. `withdrawal-soles` owns the withdrawal
operation and must call the wallet before reporting the operation as complete.

## Goals / Non-Goals

**Goals:**

- Debit the exact withdrawal amount in integer cents.
- Keep local state consistent when the wallet fails.
- Make replays and retries safe with the wallet idempotency key.
- Reverse the full amount once when a debited withdrawal is annulled.
- Prove the contract with unit, API, and end-to-end simulation tests.

**Non-Goals:**

- Implementing the wallet, user-service, or transaction-service code.
- Partial debits or partial reversals.
- Automatic reversal when ledger reporting fails while the withdrawal is valid.
- Storing card, bank, or cash-out details.

## Decisions

### 1. The application owns the debit sequence

`CreateWithdrawalUseCase` validates ownership and limits, then asks the wallet
for the wallet by integer `idUsuario`, checks the balance, and calls
`POST /payments`. The payment uses the withdrawal UUID as both
`Idempotency-Key` and `externalReference`. The movement id returned by the
wallet is stored as `wallet_movement_id` before reporting.

Alternative considered: debit inside the transaction-service report. Rejected
because transaction-service is the ledger, not the balance owner.

### 2. Identity comes from user-service

`AccountOwnership` gains `id_usuario`. The service never derives the integer
from a UUID and never keeps a UUID-to-integer table. If the field is missing,
the withdrawal fails with `DEPENDENCY_UNAVAILABLE` before any movement.

### 3. Wallet errors are translated, not leaked

| Wallet response | Withdrawal response |
| --- | --- |
| `404` | `404 WALLET_NOT_FOUND` |
| `422` insufficient balance | `422 INSUFFICIENT_BALANCE` |
| `422` inactive user | `422 USER_INACTIVE` |
| `409` | `409 WALLET_CONFLICT` |
| `401`/`403` | `503 WALLET_AUTH_FAILED` |
| timeout or other `5xx` | `503 DEPENDENCY_UNAVAILABLE` |

A raised wallet error aborts the request before commit, so the pending
withdrawal row is rolled back.

### 4. Reversal is a compensating movement

`POST /api/v1/withdrawals/{id}/reverse` requires the operation to have a
`wallet_movement_id`. It calls `/v1/movements/{movementId}/reverse` with the
canonical key `<withdrawal-id>:reverse`, stores the returned reversal movement,
moves the operation to `REVERSED`, and records the transition. A second reversal
returns `422 WALLET_ALREADY_REVERSED`.

### 5. Reporting failure does not reverse

If the wallet debit succeeds but `transaction-service` fails, the operation
remains `APPROVED` with the wallet identifiers stored. The report can be
retried. This matches the agreement: the withdrawal is still valid.

### 6. Simulation is a first-class adapter target

The local mock exposes the same wallet paths and payloads. Tests inject fake
ports; the simulation script runs the real use cases against either the mock or
the published wallet. The live run uses a `S/ 10.00` debit and reverses it, so
the seeded balance is restored.
