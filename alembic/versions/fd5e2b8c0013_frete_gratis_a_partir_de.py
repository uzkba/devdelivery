"""frete gratis a partir de um valor na configuracao de entrega

Revision ID: fd5e2b8c0013
Revises: fc4d1a9b0012
"""
from alembic import op
import sqlalchemy as sa

revision = "fd5e2b8c0013"
down_revision = "fc4d1a9b0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "configuracao_entrega",
        sa.Column("frete_gratis_a_partir_de", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("configuracao_entrega", "frete_gratis_a_partir_de")