"""Executable withdrawal rules."""

import hashlib
from decimal import Decimal
from uuid import UUID

from withdrawal_soles.domain.exceptions import DailyLimitExceeded, InvalidAmount

CURRENCY = "PEN"
MIN_AMOUNT = Decimal("10.00")
MAX_AMOUNT = Decimal("5000.00")
DAILY_LIMIT = Decimal("10000.00")
MONEY_QUANTUM = Decimal("0.01")


def validate_amount(amount: Decimal) -> Decimal:
    """Validate money precision and bounds, returning a normalized amount."""

    if amount != amount.quantize(MONEY_QUANTUM):
        raise InvalidAmount("The amount must have at most two decimal places.")
    normalized = amount.quantize(MONEY_QUANTUM)
    if normalized < MIN_AMOUNT:
        raise InvalidAmount(f"The minimum withdrawal amount is S/ {MIN_AMOUNT}.")
    if normalized > MAX_AMOUNT:
        raise InvalidAmount(f"The maximum withdrawal amount is S/ {MAX_AMOUNT}.")
    return normalized


def ensure_daily_limit(accumulated: Decimal, requested: Decimal) -> None:
    """Reject a request that would exceed the per-account daily limit."""

    projected = accumulated + requested
    if projected > DAILY_LIMIT:
        raise DailyLimitExceeded(
            accumulated=f"{accumulated:.2f}",
            requested=f"{requested:.2f}",
            limit=f"{DAILY_LIMIT:.2f}",
        )


def request_fingerprint(account_id: UUID, user_id: UUID, amount: Decimal) -> str:
    """Build a stable fingerprint for idempotency comparison."""

    payload = f"{account_id}|{user_id}|{amount.quantize(MONEY_QUANTUM):.2f}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
