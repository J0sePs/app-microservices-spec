"""Ports implemented by infrastructure adapters."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from withdrawal_soles.domain.enums import ReportStatus, WithdrawalStatus
from withdrawal_soles.domain.models import (
    AccountOwnership,
    IdempotencyRecord,
    ReportingAttempt,
    StatusChange,
    WalletBalance,
    WalletMovement,
    Withdrawal,
    WithdrawalPage,
)


class WithdrawalRepository(Protocol):
    """Persistence contract owned by the domain."""

    async def add(self, withdrawal: Withdrawal) -> None: ...

    async def save(self, withdrawal: Withdrawal) -> None: ...

    async def get(self, withdrawal_id: UUID) -> Withdrawal | None: ...

    async def list_for_user(
        self,
        user_id: UUID,
        account_id: UUID | None,
        status: WithdrawalStatus | None,
        limit: int,
        offset: int,
    ) -> WithdrawalPage: ...

    async def daily_total(
        self,
        account_id: UUID,
        start: datetime,
        end: datetime,
        statuses: tuple[WithdrawalStatus, ...],
    ) -> Decimal: ...

    async def acquire_account_lock(self, account_id: UUID) -> None: ...

    async def add_status_change(self, change: StatusChange) -> None: ...

    async def get_idempotency(self, key: str) -> IdempotencyRecord | None: ...

    async def save_idempotency(self, record: IdempotencyRecord) -> None: ...

    async def next_report_attempt_number(self, withdrawal_id: UUID) -> int: ...

    async def add_reporting_attempt(self, attempt: ReportingAttempt) -> None: ...


class UserServicePort(Protocol):
    """Ownership validation exposed by user-service."""

    async def get_ownership(
        self, account_id: UUID, user_id: UUID
    ) -> AccountOwnership: ...


class TransactionServicePort(Protocol):
    """Ledger reporting exposed by transaction-service."""

    async def report(self, withdrawal: Withdrawal) -> str: ...


class WalletServicePort(Protocol):
    """Balance owner exposed by the PEN wallet."""

    async def get_wallet(self, id_usuario: int) -> WalletBalance: ...

    async def debit(
        self,
        wallet_id: UUID,
        amount_cents: int,
        external_reference: str,
        idempotency_key: str,
    ) -> WalletMovement: ...

    async def reverse(
        self,
        movement_id: UUID,
        reason: str,
        idempotency_key: str,
    ) -> WalletMovement: ...


class Clock(Protocol):
    """Time source, injectable for deterministic tests."""

    def now(self) -> datetime: ...

    def day_bounds(self) -> tuple[datetime, datetime]: ...


class IdGenerator(Protocol):
    """Identifier source, injectable for deterministic tests."""

    def new_id(self) -> UUID: ...


__all__ = [
    "Clock",
    "IdGenerator",
    "ReportStatus",
    "TransactionServicePort",
    "UserServicePort",
    "WalletServicePort",
    "WithdrawalRepository",
]
