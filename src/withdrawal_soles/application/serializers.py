"""Stable JSON representations used by the API and idempotency snapshots."""

from datetime import UTC, datetime

from withdrawal_soles.domain.models import Withdrawal


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat().replace("+00:00", "Z")


def serialize_withdrawal(withdrawal: Withdrawal) -> dict[str, object]:
    """Serialize a withdrawal with decimal amounts as strings."""

    return {
        "id": str(withdrawal.id),
        "account_id": str(withdrawal.account_id),
        "amount": f"{withdrawal.amount:.2f}",
        "currency": withdrawal.currency,
        "status": withdrawal.status.value,
        "transaction_id": withdrawal.transaction_id,
        "wallet_id": str(withdrawal.wallet_id) if withdrawal.wallet_id else None,
        "wallet_movement_id": (
            str(withdrawal.wallet_movement_id)
            if withdrawal.wallet_movement_id
            else None
        ),
        "wallet_reversal_movement_id": (
            str(withdrawal.wallet_reversal_movement_id)
            if withdrawal.wallet_reversal_movement_id
            else None
        ),
        "created_at": _iso(withdrawal.created_at),
        "updated_at": _iso(withdrawal.updated_at),
    }
