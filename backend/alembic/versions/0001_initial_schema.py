"""Esquema inicial: assets, price_bars (hypertable), watchlist_items, alert_rules.

Revision ID: 0001
Revises:
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("quote_currency", sa.String(), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "price_bars",
        sa.Column("asset_id", sa.String(), primary_key=True),
        sa.Column("interval", sa.String(), primary_key=True),
        sa.Column("open_time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=True),
    )

    op.create_table(
        "watchlist_items",
        sa.Column("asset_id", sa.String(), primary_key=True),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("notes", sa.String(), nullable=True),
    )

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False, server_default="PRICE_CROSS"),
        sa.Column("direction", sa.String(), nullable=False, server_default="ABOVE"),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("channels", sa.String(), nullable=False, server_default="TELEGRAM"),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alert_rules_asset_id", "alert_rules", ["asset_id"])

    # Convertir price_bars en hypertable de TimescaleDB (si la extensión existe).
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute(
        "SELECT create_hypertable('price_bars', 'open_time', "
        "if_not_exists => TRUE, migrate_data => TRUE)"
    )


def downgrade() -> None:
    op.drop_index("ix_alert_rules_asset_id", table_name="alert_rules")
    op.drop_table("alert_rules")
    op.drop_table("watchlist_items")
    op.drop_table("price_bars")
    op.drop_table("assets")
