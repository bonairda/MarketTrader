"""Vínculo de Telegram por usuario.

Cada usuario puede vincular su propio chat de Telegram para recibir SUS alertas.
El bot sigue siendo único del sistema (TELEGRAM_BOT_TOKEN); lo que cambia por
usuario es el chat_id destino. El watchdog operativo sigue usando el chat global.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_telegram_links",
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("chat_id", sa.String(), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_telegram_links")
