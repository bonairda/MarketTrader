"""Ampliar alert_rules para varios tipos de alerta (indicator, timeframe).

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alert_rules", sa.Column("indicator", sa.String(), nullable=True))
    op.add_column(
        "alert_rules",
        sa.Column("timeframe", sa.String(), nullable=False, server_default="1m"),
    )


def downgrade() -> None:
    op.drop_column("alert_rules", "timeframe")
    op.drop_column("alert_rules", "indicator")
