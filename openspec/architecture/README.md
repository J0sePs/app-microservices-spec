# Architecture

This directory is the source of truth for the banking platform architecture.
Every diagram is written in mermaid so it renders on GitHub and stays reviewable
in pull requests.

## Documents

- [Project context](../../context.md) — scope, service inventory, conventions,
  and domain rules.
- [Service catalog](service-catalog.md) — responsibilities, owned databases, and
  API surfaces.
- [System context](system-context.md) — end-to-end diagram, request paths, and
  deployment topology.
- [Integration contract](integration-contract.md) — gateway, identity,
  idempotency, error envelope, and HTTP contracts.

## Entity-relationship diagrams

- [user-service](erd/user-service.md) — `user_db`
- [deposit-soles](erd/deposit-soles.md) — `deposit_soles_db`
- [deposit-dollars](erd/deposit-dollars.md) — `deposit_dollars_db`
- [withdrawal-soles](erd/withdrawal-soles.md) — `withdrawal_soles_db`
- [withdrawal-dollars](erd/withdrawal-dollars.md) — `withdrawal_dollars_db`
- [transaction-service](erd/transaction-service.md) — `transaction_db`

## Rules

1. One service owns one database. Never query another service's database.
2. Client and inter-service traffic goes through Traefik, except calls to the
   external PEN wallet, which uses its published base URL directly.
3. Every mutation requires an `Idempotency-Key`.
4. Identity is forwarded by the gateway as `X-User-Id`.
5. Update this directory in the same change that alters a boundary, table, or
   contract.
