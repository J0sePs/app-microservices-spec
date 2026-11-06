"""Domain entities and value objects."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from withdrawal_soles.domain.enums import (
    ALLOWED_TRANSITIONS,
    ReportStatus,
    WithdrawalStatus,
)
from withdrawal_soles.domain.exceptions import InvalidState


@dataclass(slots=True)
class Withdrawal:
    """A PEN withdrawal operation."""

    id: UUID
    account_id: UUID
    user_id: UUID
    amount: Decimal
    currency: str
    status: WithdrawalStatus
    created_at: datetime
    updated_at: datetime
    transaction_id: str | None = None
    wallet_user_id: int | None = None
    wallet_id: UUID | None = None
    wallet_movement_id: UUID | None = None
    wallet_reversal_movement_id: UUID | None = None
    wallet_debited_at: datetime | None = None
    wallet_reversed_at: datetime | None = None

    def transition_to(
        self,
        new_status: WithdrawalStatus,
        at: datetime,
    ) -> WithdrawalStatus:
        """Apply a state transition and return the previous status."""

        if new_status not in ALLOWED_TRANSITIONS[self.status]:
            raise InvalidState(self.status.value, new_status.value)
        previous = self.status
        self.status = new_status
        self.updated_at = at
        return previous


@dataclass(frozen=True, slots=True)
class StatusChange:
    """One entry in the withdrawal audit trail."""

    id: UUID
    withdrawal_id: UUID
    from_status: WithdrawalStatus | None
    to_status: WithdrawalStatus
    reason: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """Persisted request key, fingerprint, and resulting operation."""

    id: UUID
    key: str
    request_hash: str
    withdrawal_id: UUID
    response_snapshot: dict[str, object] | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ReportingAttempt:
    """One attempt to report an operation to the ledger."""

    id: UUID
    withdrawal_id: UUID
    attempt_number: int
    status: ReportStatus
    transaction_id: str | None
    error_message: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AccountOwnership:
    """Result of asking user-service whether an account is usable."""

    account_id: UUID
    owner_user_id: UUID
    currency: str
    status: str
    owned: bool
    id_usuario: int | None = None


@dataclass(frozen=True, slots=True)
class UserIdentity:
    """Wallet owner status returned by the users contract."""

    id_usuario: int
    active: bool


@dataclass(frozen=True, slots=True)
class WalletBalance:
    """Wallet state returned by the wallet service."""

    id: UUID
    id_usuario: int
    currency: str
    balance: int
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class WalletMovement:
    """One wallet movement created by a debit, credit, or reversal."""

    id: UUID
    wallet_id: UUID
    amount: int
    currency: str
    direction: str
    type: str
    external_reference: str | None = None
    reversal_of: UUID | None = None
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class WithdrawalPage:
    """A page of withdrawals plus the total matching count."""

    items: list[Withdrawal] = field(default_factory=list)
    total: int = 0
