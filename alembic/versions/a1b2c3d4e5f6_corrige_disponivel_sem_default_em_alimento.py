"""corrige disponivel sem server_default em alimento

Revision ID: a1b2c3d4e5f6
Revises: 8f3a1c9d2b4e
Create Date: 2026-08-22 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "8f3a1c9d2b4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # defensivo: se por algum motivo já existir linha com disponivel NULL
    # (não deveria, já que a coluna é NOT NULL, mas não custa garantir)
    op.execute("UPDATE alimento SET disponivel = true WHERE disponivel IS NULL")
    op.alter_column("alimento", "disponivel", server_default=sa.true())


def downgrade() -> None:
    op.alter_column("alimento", "disponivel", server_default=None)