"""pausa manual do restaurante

Revision ID: fa0d5c6b0010
Revises: f9c8b4e20009
"""
import sqlalchemy as sa
from alembic import op

revision = "fa0d5c6b0010"
down_revision = "f9c8b4e20009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "restaurante",
        sa.Column("pausado", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "restaurante",
        sa.Column("pausado_ate", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("restaurante", "pausado_ate")
    op.drop_column("restaurante", "pausado")