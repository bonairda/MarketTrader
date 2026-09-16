"""Usuarios y propiedad por usuario.

Crea la tabla `users` y añade `user_id` a los datos personales
(watchlist_items, alert_rules, positions). Los datos de mercado
(assets, price_bars) siguen siendo globales/compartidos.

IMPORTANTE: esta migración VACÍA las tablas personales existentes
(watchlist_items, alert_rules, positions) porque sus filas no tienen dueño
y el modelo pasa a exigir `user_id`. Es seguro en un proyecto personal sin
datos reales todavía; si hubiera datos, habría que asignarlos a un usuario
antes de migrar.

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="OWNER"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ux_users_email", "users", ["email"], unique=True)

    # Vaciar datos personales sin dueño antes de exigir user_id.
    op.execute("DELETE FROM watchlist_items")
    op.execute("DELETE FROM alert_rules")
    op.execute("DELETE FROM positions")

    # watchlist_items: la PK pasa a ser compuesta (user_id, asset_id).
    op.drop_constraint("watchlist_items_pkey", "watchlist_items", type_="primary")
    op.add_column("watchlist_items", sa.Column("user_id", sa.String(), nullable=False))
    op.create_primary_key(
        "watchlist_items_pkey", "watchlist_items", ["user_id", "asset_id"]
    )

    # alert_rules: user_id + índice para filtrar por usuario.
    op.add_column("alert_rules", sa.Column("user_id", sa.String(), nullable=False))
    op.create_index("ix_alert_rules_user_id", "alert_rules", ["user_id"])

    # positions: user_id + índice.
    op.add_column("positions", sa.Column("user_id", sa.String(), nullable=False))
    op.create_index("ix_positions_user_id", "positions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_positions_user_id", table_name="positions")
    op.drop_column("positions", "user_id")

    op.drop_index("ix_alert_rules_user_id", table_name="alert_rules")
    op.drop_column("alert_rules", "user_id")

    op.drop_constraint("watchlist_items_pkey", "watchlist_items", type_="primary")
    op.drop_column("watchlist_items", "user_id")
    op.create_primary_key("watchlist_items_pkey", "watchlist_items", ["asset_id"])

    op.drop_index("ux_users_email", table_name="users")
    op.drop_table("users")
