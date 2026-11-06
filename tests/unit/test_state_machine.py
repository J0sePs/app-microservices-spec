"""Tests for the withdrawal state machine."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from withdrawal_soles.domain.enums import WithdrawalStatus
from withdrawal_soles.domain.exceptions import InvalidState
from withdrawal_soles.domain.models import Withdrawal


def make_withdrawal(status: WithdrawalStatus = WithdrawalStatus.PENDING) -> Withdrawal:
    now = datetime(2026, 10, 30, tzinfo=UTC)
    return Withdrawal(
        id=uuid4(),
        account_id=uuid4(),
        user_id=uuid4(),
        amount=Decimal("250.00"),
        currency="PEN",
        status=status,
        created_at=now,
        updated_at=now,
    )


def test_pending_can_be_approved_or_rejected() -> None:
    approved = make_withdrawal()
    assert approved.transition_to(WithdrawalStatus.APPROVED, datetime.now(UTC)) == (
        WithdrawalStatus.PENDING
    )
    rejected = make_withdrawal()
    rejected.transition_to(WithdrawalStatus.REJECTED, datetime.now(UTC))
    assert rejected.status == WithdrawalStatus.REJECTED


def test_approved_can_complete_or_fail() -> None:
    withdrawal = make_withdrawal(WithdrawalStatus.APPROVED)
    withdrawal.transition_to(WithdrawalStatus.COMPLETED, datetime.now(UTC))
    assert withdrawal.status == WithdrawalStatus.COMPLETED

    failed = make_withdrawal(WithdrawalStatus.APPROVED)
    failed.transition_to(WithdrawalStatus.FAILED, datetime.now(UTC))
    assert failed.status == WithdrawalStatus.FAILED


def test_debited_states_can_be_reversed() -> None:
    for status in (
        WithdrawalStatus.APPROVED,
        WithdrawalStatus.COMPLETED,
        WithdrawalStatus.FAILED,
    ):
        withdrawal = make_withdrawal(status)
        withdrawal.transition_to(WithdrawalStatus.REVERSED, datetime.now(UTC))
        assert withdrawal.status == WithdrawalStatus.REVERSED


def test_terminal_states_cannot_transition() -> None:
    for status in (
        WithdrawalStatus.COMPLETED,
        WithdrawalStatus.REJECTED,
        WithdrawalStatus.FAILED,
        WithdrawalStatus.REVERSED,
    ):
        with pytest.raises(InvalidState):
            make_withdrawal(status).transition_to(
                WithdrawalStatus.PENDING, datetime.now(UTC)
            )
