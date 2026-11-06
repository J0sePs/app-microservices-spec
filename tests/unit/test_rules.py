"""Tests for executable withdrawal rules."""

from decimal import Decimal
from uuid import UUID

import pytest

from withdrawal_soles.domain.exceptions import DailyLimitExceeded, InvalidAmount
from withdrawal_soles.domain.rules import (
    DAILY_LIMIT,
    amount_to_cents,
    ensure_daily_limit,
    request_fingerprint,
    validate_amount,
)

ACCOUNT_ID = UUID("1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11")
USER_ID = UUID("9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f")


@pytest.mark.parametrize("amount", ["10.00", "250.50", "5000.00"])
def test_amount_within_bounds_is_accepted(amount: str) -> None:
    assert validate_amount(Decimal(amount)) == Decimal(amount)


@pytest.mark.parametrize("amount", ["9.99", "0.00", "-10.00", "5000.01"])
def test_amount_outside_bounds_is_rejected(amount: str) -> None:
    with pytest.raises(InvalidAmount):
        validate_amount(Decimal(amount))


def test_amount_with_three_significant_decimals_is_rejected() -> None:
    with pytest.raises(InvalidAmount):
        validate_amount(Decimal("10.001"))


def test_trailing_zeroes_are_normalized() -> None:
    assert validate_amount(Decimal("10.000")) == Decimal("10.00")


def test_daily_limit_boundary_is_inclusive() -> None:
    ensure_daily_limit(Decimal("5000.00"), Decimal("5000.00"))


def test_daily_limit_excess_is_rejected() -> None:
    with pytest.raises(DailyLimitExceeded) as error:
        ensure_daily_limit(Decimal("9900.00"), Decimal("200.00"))
    assert error.value.code == "DAILY_LIMIT_EXCEEDED"
    assert error.value.details["limit"] == "10000.00"


def test_daily_limit_constant() -> None:
    assert DAILY_LIMIT == Decimal("10000.00")


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("10.00", 1000), ("250.00", 25000), ("250.50", 25050), ("5000.00", 500000)],
)
def test_amount_is_converted_to_exact_cents(amount: str, expected: int) -> None:
    assert amount_to_cents(Decimal(amount)) == expected


def test_fingerprint_is_stable_and_body_sensitive() -> None:
    first = request_fingerprint(ACCOUNT_ID, USER_ID, Decimal("250.00"))
    second = request_fingerprint(ACCOUNT_ID, USER_ID, Decimal("250.0"))
    different = request_fingerprint(ACCOUNT_ID, USER_ID, Decimal("250.01"))
    assert first == second
    assert first != different
