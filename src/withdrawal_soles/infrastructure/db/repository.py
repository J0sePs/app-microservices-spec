"""SQLAlchemy repository implementing the domain persistence port."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from withdrawal_soles.domain.enums import WithdrawalStatus
from withdrawal_soles.domain.models import (
    IdempotencyRecord,
    ReportingAttempt,
    StatusChange,
    Withdrawal,
    WithdrawalPage,
)
from withdrawal_soles.infrastructure.db.mappers import (
    attempt_to_model,
    idempotency_to_domain,
    idempotency_to_model,
    status_change_to_model,
    withdrawal_to_domain,
    withdrawal_to_model,
)
from withdrawal_soles.infrastructure.db.models import (
    IdempotencyRecordModel,
    ReportingAttemptModel,
    WithdrawalOperation,
)


class SQLAlchemyWithdrawalRepository:
    """PostgreSQL-backed implementation of ``WithdrawalRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, withdrawal: Withdrawal) -> None:
        self._session.add(withdrawal_to_model(withdrawal))
        await self._session.flush()

    async def save(self, withdrawal: Withdrawal) -> None:
        row = await self._session.get(WithdrawalOperation, withdrawal.id)
        if row is None:
            from withdrawal_soles.domain.exceptions import WithdrawalNotFound

            raise WithdrawalNotFound()
        row.account_id = withdrawal.account_id
        row.user_id = withdrawal.user_id
        row.amount = withdrawal.amount
        row.currency = withdrawal.currency
        row.status = withdrawal.status.value
        row.transaction_id = withdrawal.transaction_id
        row.wallet_user_id = withdrawal.wallet_user_id
        row.wallet_id = withdrawal.wallet_id
        row.wallet_movement_id = withdrawal.wallet_movement_id
        row.wallet_reversal_movement_id = withdrawal.wallet_reversal_movement_id
        row.wallet_debited_at = withdrawal.wallet_debited_at
        row.wallet_reversed_at = withdrawal.wallet_reversed_at
        row.updated_at = withdrawal.updated_at
        await self._session.flush()

    async def get(self, withdrawal_id: UUID) -> Withdrawal | None:
        row = await self._session.get(WithdrawalOperation, withdrawal_id)
        return withdrawal_to_domain(row) if row is not None else None

    async def list_for_user(
        self,
        user_id: UUID,
        account_id: UUID | None,
        status: WithdrawalStatus | None,
        limit: int,
        offset: int,
    ) -> WithdrawalPage:
        conditions = [WithdrawalOperation.user_id == user_id]
        if account_id is not None:
            conditions.append(WithdrawalOperation.account_id == account_id)
        if status is not None:
            conditions.append(WithdrawalOperation.status == status.value)

        total = await self._session.scalar(
            select(func.count())
            .select_from(WithdrawalOperation)
            .where(*conditions)
        )
        result = await self._session.scalars(
            select(WithdrawalOperation)
            .where(*conditions)
            .order_by(WithdrawalOperation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return WithdrawalPage(
            items=[withdrawal_to_domain(row) for row in result.all()],
            total=int(total or 0),
        )

    async def daily_total(
        self,
        account_id: UUID,
        start: datetime,
        end: datetime,
        statuses: tuple[WithdrawalStatus, ...],
    ) -> Decimal:
        value = await self._session.scalar(
            select(func.coalesce(func.sum(WithdrawalOperation.amount), 0)).where(
                WithdrawalOperation.account_id == account_id,
                WithdrawalOperation.status.in_([status.value for status in statuses]),
                WithdrawalOperation.created_at >= start,
                WithdrawalOperation.created_at < end,
            )
        )
        return Decimal(str(value or 0))

    async def acquire_account_lock(self, account_id: UUID) -> None:
        if self._session.bind is None:
            return
        if self._session.bind.dialect.name != "postgresql":
            return
        await self._session.execute(
            text(
                "SELECT pg_advisory_xact_lock(hashtext(:account_id)::bigint)"
            ),
            {"account_id": str(account_id)},
        )

    async def add_status_change(self, change: StatusChange) -> None:
        self._session.add(status_change_to_model(change))
        await self._session.flush()

    async def get_idempotency(self, key: str) -> IdempotencyRecord | None:
        row = await self._session.scalar(
            select(IdempotencyRecordModel).where(IdempotencyRecordModel.key == key)
        )
        return idempotency_to_domain(row) if row is not None else None

    async def save_idempotency(self, record: IdempotencyRecord) -> None:
        self._session.add(idempotency_to_model(record))
        await self._session.flush()

    async def next_report_attempt_number(self, withdrawal_id: UUID) -> int:
        current = await self._session.scalar(
            select(func.coalesce(func.max(ReportingAttemptModel.attempt_number), 0))
            .where(ReportingAttemptModel.withdrawal_id == withdrawal_id)
        )
        return int(current or 0) + 1

    async def add_reporting_attempt(self, attempt: ReportingAttempt) -> None:
        self._session.add(attempt_to_model(attempt))
        await self._session.flush()
