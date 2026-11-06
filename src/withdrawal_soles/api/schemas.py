"""Pydantic schemas for the public HTTP contract."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from withdrawal_soles.domain.enums import WithdrawalStatus
from withdrawal_soles.domain.models import Withdrawal


class WithdrawalCreate(BaseModel):
    """Payload for creating a PEN withdrawal."""

    model_config = ConfigDict(extra="forbid")

    account_id: UUID
    amount: Decimal = Field(..., max_digits=12, decimal_places=2)

    @field_validator("amount")
    @classmethod
    def validate_precision(cls, value: Decimal) -> Decimal:
        if value != value.quantize(Decimal("0.01")):
            raise ValueError("The amount must have at most two decimal places.")
        return value


class WithdrawalResponse(BaseModel):
    """Public representation of a withdrawal."""

    id: UUID
    account_id: UUID
    amount: str
    currency: str
    status: WithdrawalStatus
    transaction_id: str | None
    wallet_id: UUID | None = None
    wallet_movement_id: UUID | None = None
    wallet_reversal_movement_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, withdrawal: Withdrawal) -> "WithdrawalResponse":
        return cls(
            id=withdrawal.id,
            account_id=withdrawal.account_id,
            amount=f"{withdrawal.amount:.2f}",
            currency=withdrawal.currency,
            status=withdrawal.status,
            transaction_id=withdrawal.transaction_id,
            wallet_id=withdrawal.wallet_id,
            wallet_movement_id=withdrawal.wallet_movement_id,
            wallet_reversal_movement_id=withdrawal.wallet_reversal_movement_id,
            created_at=withdrawal.created_at,
            updated_at=withdrawal.updated_at,
        )


class WithdrawalReverse(BaseModel):
    """Payload for reversing a debited withdrawal."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=1, max_length=500)


class WithdrawalListResponse(BaseModel):
    """Paginated withdrawal list."""

    items: list[WithdrawalResponse]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    """Stable error envelope returned by every failing endpoint."""

    code: str
    message: str
    details: dict[str, Any]


class HealthResponse(BaseModel):
    """Health response body."""

    status: str
