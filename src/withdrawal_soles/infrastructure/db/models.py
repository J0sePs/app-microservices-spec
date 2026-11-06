"""SQLAlchemy models for withdrawal_soles_db."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from withdrawal_soles.infrastructure.db.base import Base, JSONType


class WithdrawalOperation(Base):
    __tablename__ = "withdrawal_operations"
    __table_args__ = (
        CheckConstraint("amount >= 10.00 AND amount <= 5000.00", name="ck_amount_range"),
        CheckConstraint("currency = 'PEN'", name="ck_currency_pen"),
        CheckConstraint(
            "status IN ("
            "'PENDING', 'APPROVED', 'REJECTED', 'COMPLETED', 'FAILED', 'REVERSED'"
            ")",
            name="ck_status",
        ),
        Index("ix_withdrawal_operations_account_created", "account_id", "created_at"),
        Index("ix_withdrawal_operations_user_created", "user_id", "created_at"),
        Index("ix_withdrawal_operations_wallet", "wallet_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PEN")
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    wallet_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wallet_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    wallet_movement_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    wallet_reversal_movement_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    wallet_debited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    wallet_reversed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WithdrawalStatusHistory(Base):
    __tablename__ = "withdrawal_status_history"
    __table_args__ = (
        Index("ix_status_history_withdrawal_created", "withdrawal_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    withdrawal_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("withdrawal_operations.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IdempotencyRecordModel(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    withdrawal_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("withdrawal_operations.id", ondelete="CASCADE"),
        nullable=False,
    )
    response_snapshot: Mapped[dict[str, object] | None] = mapped_column(
        JSONType, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReportingAttemptModel(Base):
    __tablename__ = "reporting_attempts"
    __table_args__ = (
        UniqueConstraint(
            "withdrawal_id", "attempt_number", name="uq_reporting_attempt"
        ),
        Index("ix_reporting_attempts_withdrawal", "withdrawal_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    withdrawal_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("withdrawal_operations.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
