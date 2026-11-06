"""Mapping between persistence models and domain entities."""

from datetime import UTC, datetime
from decimal import Decimal

from withdrawal_soles.domain.enums import ReportStatus, WithdrawalStatus
from withdrawal_soles.domain.models import (
    IdempotencyRecord,
    ReportingAttempt,
    StatusChange,
    Withdrawal,
)
from withdrawal_soles.infrastructure.db.models import (
    IdempotencyRecordModel,
    ReportingAttemptModel,
    WithdrawalOperation,
    WithdrawalStatusHistory,
)


def utc(value: datetime) -> datetime:
    """Normalize database timestamps to aware UTC values."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def withdrawal_to_domain(row: WithdrawalOperation) -> Withdrawal:
    return Withdrawal(
        id=row.id,
        account_id=row.account_id,
        user_id=row.user_id,
        amount=Decimal(row.amount),
        currency=row.currency,
        status=WithdrawalStatus(row.status),
        transaction_id=row.transaction_id,
        wallet_user_id=row.wallet_user_id,
        wallet_id=row.wallet_id,
        wallet_movement_id=row.wallet_movement_id,
        wallet_reversal_movement_id=row.wallet_reversal_movement_id,
        wallet_debited_at=utc(row.wallet_debited_at)
        if row.wallet_debited_at is not None
        else None,
        wallet_reversed_at=utc(row.wallet_reversed_at)
        if row.wallet_reversed_at is not None
        else None,
        created_at=utc(row.created_at),
        updated_at=utc(row.updated_at),
    )


def withdrawal_to_model(withdrawal: Withdrawal) -> WithdrawalOperation:
    return WithdrawalOperation(
        id=withdrawal.id,
        account_id=withdrawal.account_id,
        user_id=withdrawal.user_id,
        amount=withdrawal.amount,
        currency=withdrawal.currency,
        status=withdrawal.status.value,
        transaction_id=withdrawal.transaction_id,
        wallet_user_id=withdrawal.wallet_user_id,
        wallet_id=withdrawal.wallet_id,
        wallet_movement_id=withdrawal.wallet_movement_id,
        wallet_reversal_movement_id=withdrawal.wallet_reversal_movement_id,
        wallet_debited_at=withdrawal.wallet_debited_at,
        wallet_reversed_at=withdrawal.wallet_reversed_at,
        created_at=withdrawal.created_at,
        updated_at=withdrawal.updated_at,
    )


def status_change_to_model(change: StatusChange) -> WithdrawalStatusHistory:
    return WithdrawalStatusHistory(
        id=change.id,
        withdrawal_id=change.withdrawal_id,
        from_status=change.from_status.value if change.from_status else None,
        to_status=change.to_status.value,
        reason=change.reason,
        created_at=change.created_at,
    )


def idempotency_to_domain(row: IdempotencyRecordModel) -> IdempotencyRecord:
    return IdempotencyRecord(
        id=row.id,
        key=row.key,
        request_hash=row.request_hash,
        withdrawal_id=row.withdrawal_id,
        response_snapshot=row.response_snapshot,
        created_at=utc(row.created_at),
    )


def idempotency_to_model(record: IdempotencyRecord) -> IdempotencyRecordModel:
    return IdempotencyRecordModel(
        id=record.id,
        key=record.key,
        request_hash=record.request_hash,
        withdrawal_id=record.withdrawal_id,
        response_snapshot=record.response_snapshot,
        created_at=record.created_at,
    )


def attempt_to_model(attempt: ReportingAttempt) -> ReportingAttemptModel:
    return ReportingAttemptModel(
        id=attempt.id,
        withdrawal_id=attempt.withdrawal_id,
        attempt_number=attempt.attempt_number,
        status=attempt.status.value,
        transaction_id=attempt.transaction_id,
        error_message=attempt.error_message,
        created_at=attempt.created_at,
    )


def attempt_to_domain(row: ReportingAttemptModel) -> ReportingAttempt:
    return ReportingAttempt(
        id=row.id,
        withdrawal_id=row.withdrawal_id,
        attempt_number=row.attempt_number,
        status=ReportStatus(row.status),
        transaction_id=row.transaction_id,
        error_message=row.error_message,
        created_at=utc(row.created_at),
    )


__all__ = [
    "attempt_to_domain",
    "attempt_to_model",
    "idempotency_to_domain",
    "idempotency_to_model",
    "status_change_to_model",
    "withdrawal_to_domain",
    "withdrawal_to_model",
]
