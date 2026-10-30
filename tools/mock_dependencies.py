"""Local-only stubs for user-service and transaction-service.

The real services are separate repositories. These endpoints let the compose
stack exercise the full withdrawal flow without them.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(
    title="mock-dependencies",
    description="Local stubs for user-service and transaction-service.",
)

_transactions: dict[tuple[str, str], dict[str, object]] = {}


class TransactionReport(BaseModel):
    source_service: str
    source_operation_id: str
    account_id: UUID
    type: str
    amount: str
    currency: str
    status: str
    occurred_at: datetime


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/accounts/{account_id}/ownership")
async def ownership(
    account_id: UUID,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    owned: bool = Query(default=True),
    currency: str = Query(default="PEN"),
    status: str = Query(default="ACTIVE"),
) -> dict[str, object]:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="missing identity")
    return {
        "account_id": str(account_id),
        "owner_user_id": x_user_id,
        "currency": currency,
        "status": status,
        "owned": owned,
    }


@app.post("/api/v1/transactions", status_code=201)
async def report_transaction(
    payload: TransactionReport,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key")
    ] = None,
) -> dict[str, object]:
    if not x_user_id or not idempotency_key:
        raise HTTPException(status_code=401, detail="missing identity")
    key = (payload.source_service, payload.source_operation_id)
    existing = _transactions.get(key)
    if existing is not None:
        return existing

    transaction = {
        "transaction_id": str(uuid4()),
        "source_service": payload.source_service,
        "source_operation_id": payload.source_operation_id,
        "account_id": str(payload.account_id),
        "type": payload.type,
        "amount": payload.amount,
        "currency": payload.currency,
        "status": payload.status,
        "created_at": datetime.now().isoformat(),
    }
    _transactions[key] = transaction
    return transaction
