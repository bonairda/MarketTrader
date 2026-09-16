"""Libro de operaciones de inversión y trazabilidad fiscal.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quantity", sa.Numeric(30, 12), nullable=False),
        sa.Column("unit_price_original", sa.Numeric(30, 12), nullable=False),
        sa.Column("gross_amount_original", sa.Numeric(30, 12), nullable=False),
        sa.Column(
            "fees_original",
            sa.Numeric(30, 12),
            nullable=False,
            server_default="0",
        ),
        sa.Column("currency", sa.String(length=12), nullable=False),
        sa.Column("fx_rate_to_eur", sa.Numeric(24, 12), nullable=False),
        sa.Column("fx_source", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False, server_default="MANUAL"),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_operations_side"),
        sa.CheckConstraint("quantity > 0", name="ck_operations_quantity_positive"),
        sa.CheckConstraint(
            "unit_price_original > 0", name="ck_operations_unit_price_positive"
        ),
        sa.CheckConstraint(
            "gross_amount_original > 0", name="ck_operations_gross_positive"
        ),
        sa.CheckConstraint(
            "fees_original >= 0", name="ck_operations_fees_nonnegative"
        ),
        sa.CheckConstraint(
            "fees_original <= gross_amount_original",
            name="ck_operations_fees_not_above_gross",
        ),
        sa.CheckConstraint("fx_rate_to_eur > 0", name="ck_operations_fx_positive"),
    )
    op.create_index(
        "ix_operations_user_asset_order",
        "operations",
        ["user_id", "asset_id", "trade_date", "executed_at", "id"],
    )
    op.create_index(
        "ix_operations_user_trade_date", "operations", ["user_id", "trade_date"]
    )
    op.create_index(
        "ux_operations_user_source_external_id",
        "operations",
        ["user_id", "source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_table(
        "operation_audit_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Sin FK a operations: el snapshot debe sobrevivir al borrado.
        sa.Column("operation_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "action IN ('CREATE', 'DELETE')", name="ck_operation_audit_action"
        ),
    )
    op.create_index(
        "ix_operation_audit_user_operation",
        "operation_audit_log",
        ["user_id", "operation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_operation_audit_user_operation", table_name="operation_audit_log"
    )
    op.drop_table("operation_audit_log")
    op.drop_index("ux_operations_user_source_external_id", table_name="operations")
    op.drop_index("ix_operations_user_trade_date", table_name="operations")
    op.drop_index("ix_operations_user_asset_order", table_name="operations")
    op.drop_table("operations")
