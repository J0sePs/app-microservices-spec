"""Create withdrawal tables.

Revision ID: 0001_create_withdrawal_tables
Revises:
Create Date: 2026-10-30

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_withdrawal_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "withdrawal_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "currency", sa.String(length=3), nullable=False, server_default="PEN"
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("transaction_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "amount >= 10.00 AND amount <= 5000.00", name="ck_amount_range"
        ),
        sa.CheckConstraint("currency = 'PEN'", name="ck_currency_pen"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'COMPLETED', 'FAILED')",
            name="ck_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_withdrawal_operations_account_created",
        "withdrawal_operations",
        ["account_id", "created_at"],
    )
    op.create_index(
        "ix_withdrawal_operations_user_created",
        "withdrawal_operations",
        ["user_id", "created_at"],
    )

    op.create_table(
        "withdrawal_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("withdrawal_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=16), nullable=True),
        sa.Column("to_status", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["withdrawal_id"], ["withdrawal_operations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_status_history_withdrawal_created",
        "withdrawal_status_history",
        ["withdrawal_id", "created_at"],
    )

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("withdrawal_id", sa.Uuid(), nullable=False),
        sa.Column("response_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["withdrawal_id"], ["withdrawal_operations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_idempotency_key"),
    )

    op.create_table(
        "reporting_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("withdrawal_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("transaction_id", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["withdrawal_id"], ["withdrawal_operations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "withdrawal_id",
            "attempt_number",
            name="uq_reporting_attempt",
        ),
    )
    op.create_index(
        "ix_reporting_attempts_withdrawal",
        "reporting_attempts",
        ["withdrawal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reporting_attempts_withdrawal", table_name="reporting_attempts"
    )
    op.drop_table("reporting_attempts")
    op.drop_table("idempotency_records")
    op.drop_index(
        "ix_status_history_withdrawal_created",
        table_name="withdrawal_status_history",
    )
    op.drop_table("withdrawal_status_history")
    op.drop_index(
        "ix_withdrawal_operations_user_created",
        table_name="withdrawal_operations",
    )
    op.drop_index(
        "ix_withdrawal_operations_account_created",
        table_name="withdrawal_operations",
    )
    op.drop_table("withdrawal_operations")
