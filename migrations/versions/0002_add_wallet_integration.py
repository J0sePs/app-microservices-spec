"""Add wallet debit and reversal columns.

Revision ID: 0002_add_wallet_integration
Revises: 0001_create_withdrawal_tables
Create Date: 2026-11-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_wallet_integration"
down_revision: str | None = "0001_create_withdrawal_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "withdrawal_operations",
        sa.Column("wallet_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "withdrawal_operations",
        sa.Column("wallet_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "withdrawal_operations",
        sa.Column("wallet_movement_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "withdrawal_operations",
        sa.Column("wallet_reversal_movement_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "withdrawal_operations",
        sa.Column("wallet_debited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "withdrawal_operations",
        sa.Column("wallet_reversed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_withdrawal_operations_wallet",
        "withdrawal_operations",
        ["wallet_id"],
    )

    op.drop_constraint("ck_status", "withdrawal_operations", type_="check")
    op.create_check_constraint(
        "ck_status",
        "withdrawal_operations",
        "status IN ("
        "'PENDING', 'APPROVED', 'REJECTED', 'COMPLETED', 'FAILED', 'REVERSED'"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint("ck_status", "withdrawal_operations", type_="check")
    op.create_check_constraint(
        "ck_status",
        "withdrawal_operations",
        "status IN ('PENDING', 'APPROVED', 'REJECTED', 'COMPLETED', 'FAILED')",
    )
    op.drop_index(
        "ix_withdrawal_operations_wallet", table_name="withdrawal_operations"
    )
    op.drop_column("withdrawal_operations", "wallet_reversed_at")
    op.drop_column("withdrawal_operations", "wallet_debited_at")
    op.drop_column("withdrawal_operations", "wallet_reversal_movement_id")
    op.drop_column("withdrawal_operations", "wallet_movement_id")
    op.drop_column("withdrawal_operations", "wallet_id")
    op.drop_column("withdrawal_operations", "wallet_user_id")
