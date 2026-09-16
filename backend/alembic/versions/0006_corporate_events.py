"""Eventos corporativos: dividendos (con retención) y splits.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "corporate_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("gross_amount_original", sa.Numeric(30, 12), nullable=True),
        sa.Column("withholding_original", sa.Numeric(30, 12), nullable=True),
        sa.Column("currency", sa.String(length=12), nullable=True),
        sa.Column("fx_rate_to_eur", sa.Numeric(24, 12), nullable=True),
        sa.Column("ratio", sa.Numeric(24, 12), nullable=True),
        sa.Column("fx_source", sa.String(), nullable=True),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "type IN ('DIVIDEND', 'SPLIT')", name="ck_corporate_events_type"
        ),
    )
    op.create_index(
        "ix_corporate_events_user_asset_date",
        "corporate_events",
        ["user_id", "asset_id", "event_date"],
    )
    op.create_index(
        "ux_corporate_events_user_external_id",
        "corporate_events",
        ["user_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_corporate_events_user_external_id", table_name="corporate_events"
    )
    op.drop_index(
        "ix_corporate_events_user_asset_date", table_name="corporate_events"
    )
    op.drop_table("corporate_events")
