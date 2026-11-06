"""Domain enums for withdrawal operations."""

from enum import StrEnum


class WithdrawalStatus(StrEnum):
    """Lifecycle states allowed for a withdrawal."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class ReportStatus(StrEnum):
    """Outcome of one ledger reporting attempt."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


ALLOWED_TRANSITIONS: dict[WithdrawalStatus, frozenset[WithdrawalStatus]] = {
    WithdrawalStatus.PENDING: frozenset(
        {WithdrawalStatus.APPROVED, WithdrawalStatus.REJECTED}
    ),
    WithdrawalStatus.APPROVED: frozenset(
        {
            WithdrawalStatus.COMPLETED,
            WithdrawalStatus.FAILED,
            WithdrawalStatus.REVERSED,
        }
    ),
    WithdrawalStatus.REJECTED: frozenset(),
    WithdrawalStatus.COMPLETED: frozenset({WithdrawalStatus.REVERSED}),
    WithdrawalStatus.FAILED: frozenset({WithdrawalStatus.REVERSED}),
    WithdrawalStatus.REVERSED: frozenset(),
}

COUNTED_DAILY_STATUSES = (
    WithdrawalStatus.PENDING,
    WithdrawalStatus.APPROVED,
    WithdrawalStatus.COMPLETED,
)
