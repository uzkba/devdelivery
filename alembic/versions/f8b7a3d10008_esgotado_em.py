"""esgotado_em em marmita, combo e alimento

Revision ID: f8b7a3d10008
Revises: f7a6f2c50007
"""
from alembic import op
import sqlalchemy as sa

revision = "f8b7a3d10008"
down_revision = "f7a6f2c50007"
branch_labels = None
depends_on = None

TABELAS = ("marmita", "combo", "alimento")


def upgrade() -> None:
    for tabela in TABELAS:
        op.add_column(tabela, sa.Column("esgotado_em", sa.Date(), nullable=True))


def downgrade() -> None:
    for tabela in reversed(TABELAS):
        op.drop_column(tabela, "esgotado_em")