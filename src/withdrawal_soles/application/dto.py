"""Application DTOs and result objects."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from withdrawal_soles.domain.models import Withdrawal


@dataclass(frozen=True, slots=True)
class CreateWithdrawalCommand:
    account_id: UUID
    amount: Decimal
    user_id: UUID
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class CreateWithdrawalResult:
    withdrawal: Withdrawal
    replayed: bool


@dataclass(frozen=True, slots=True)
class RetryReportResult:
    withdrawal: Withdrawal
    reported: bool
