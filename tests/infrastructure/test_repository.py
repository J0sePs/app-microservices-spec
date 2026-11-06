"""Tests for the SQLAlchemy repository."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text

from tests.conftest import ACCOUNT_ID, USER_ID
from withdrawal_soles.domain.enums import ReportStatus, WithdrawalStatus
from withdrawal_soles.domain.models import (
    IdempotencyRecord,
    ReportingAttempt,
    StatusChange,
    Withdrawal,
)
from withdrawal_soles.infrastructure.db.repository import (
    SQLAlchemyWithdrawalRepository,
)


def make_withdrawal(status: WithdrawalStatus = WithdrawalStatus.PENDING) -> Withdrawal:
    now = datetime(2026, 10, 30, 15, 0, tzinfo=UTC)
    return Withdrawal(
        id=uuid4(),
        account_id=ACCOUNT_ID,
        user_id=USER_ID,
        amount=Decimal("250.00"),
        currency="PEN",
        status=status,
        created_at=now,
        updated_at=now,
    )


async def test_session_executes_select_one(session) -> None:
    result = await session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


async def test_add_get_and_save(session) -> None:
    repository = SQLAlchemyWithdrawalRepository(session)
    value = make_withdrawal()
    await repository.add(value)
    fetched = await repository.get(value.id)
    assert fetched is not None
    assert fetched.status == WithdrawalStatus.PENDING

    fetched.transaction_id = "tx-1"
    fetched.transition_to(WithdrawalStatus.APPROVED, datetime.now(UTC))
    await repository.save(fetched)
    updated = await repository.get(value.id)
    assert updated is not None
    assert updated.status == WithdrawalStatus.APPROVED
    assert updated.transaction_id == "tx-1"


async def test_list_for_user_with_filters(session) -> None:
    repository = SQLAlchemyWithdrawalRepository(session)
    for _ in range(3):
        await repository.add(make_withdrawal())
    await session.commit()

    page = await repository.list_for_user(
        USER_ID, ACCOUNT_ID, WithdrawalStatus.PENDING, limit=2, offset=0
    )
    assert page.total == 3
    assert len(page.items) == 2

    empty = await repository.list_for_user(
        USER_ID, ACCOUNT_ID, WithdrawalStatus.COMPLETED, limit=2, offset=0
    )
    assert empty.total == 0


async def test_daily_total_counts_only_selected_statuses(session) -> None:
    repository = SQLAlchemyWithdrawalRepository(session)
    now = datetime(2026, 10, 30, 15, 0, tzinfo=UTC)
    for amount, status in (
        ("100.00", WithdrawalStatus.PENDING),
        ("200.00", WithdrawalStatus.COMPLETED),
        ("300.00", WithdrawalStatus.REJECTED),
    ):
        value = make_withdrawal(status)
        value.amount = Decimal(amount)
        await repository.add(value)
    await session.commit()

    total = await repository.daily_total(
        ACCOUNT_ID,
        now - timedelta(hours=1),
        now + timedelta(hours=1),
        (
            WithdrawalStatus.PENDING,
            WithdrawalStatus.APPROVED,
            WithdrawalStatus.COMPLETED,
        ),
    )
    assert total == Decimal("300.00")


async def test_wallet_fields_round_trip(session) -> None:
    repository = SQLAlchemyWithdrawalRepository(session)
    value = make_withdrawal()
    wallet_id = uuid4()
    movement_id = uuid4()
    value.wallet_user_id = 15
    value.wallet_id = wallet_id
    value.wallet_movement_id = movement_id
    value.wallet_debited_at = datetime(2026, 11, 6, 20, 0, tzinfo=UTC)
    await repository.add(value)
    await session.commit()

    fetched = await repository.get(value.id)
    assert fetched is not None
    assert fetched.wallet_user_id == 15
    assert fetched.wallet_id == wallet_id
    assert fetched.wallet_movement_id == movement_id
    assert fetched.wallet_debited_at == datetime(
        2026, 11, 6, 20, 0, tzinfo=UTC
    )


async def test_idempotency_and_reporting_attempts(session) -> None:
    repository = SQLAlchemyWithdrawalRepository(session)
    value = make_withdrawal()
    await repository.add(value)
    await repository.add_status_change(
        StatusChange(
            id=uuid4(),
            withdrawal_id=value.id,
            from_status=None,
            to_status=WithdrawalStatus.PENDING,
            reason="created",
            created_at=value.created_at,
        )
    )
    await repository.save_idempotency(
        IdempotencyRecord(
            id=uuid4(),
            key="repo-key",
            request_hash="hash",
            withdrawal_id=value.id,
            response_snapshot={"id": str(value.id)},
            created_at=value.created_at,
        )
    )
    assert (await repository.get_idempotency("repo-key")) is not None
    assert await repository.next_report_attempt_number(value.id) == 1

    await repository.add_reporting_attempt(
        ReportingAttempt(
            id=uuid4(),
            withdrawal_id=value.id,
            attempt_number=1,
            status=ReportStatus.FAILED,
            transaction_id=None,
            error_message="timeout",
            created_at=value.created_at,
        )
    )
    assert await repository.next_report_attempt_number(value.id) == 2
    await session.commit()
