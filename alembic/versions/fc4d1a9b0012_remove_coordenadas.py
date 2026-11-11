"""remove coordenadas de restaurante e endereco_cliente (sem uso apos o fim da entrega por distancia)

Revision ID: fc4d1a9b0012
Revises: fb2a9d7e0011
"""
from alembic import op
import sqlalchemy as sa

revision = "fc4d1a9b0012"
down_revision = "fb2a9d7e0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("endereco_cliente", "longitude")
    op.drop_column("endereco_cliente", "latitude")
    op.drop_column("restaurante", "longitude")
    op.drop_column("restaurante", "latitude")


def downgrade() -> None:
    op.add_column("restaurante", sa.Column("latitude", sa.Numeric(10, 8), nullable=True))
    op.add_column("restaurante", sa.Column("longitude", sa.Numeric(11, 8), nullable=True))
    op.add_column("endereco_cliente", sa.Column("latitude", sa.Numeric(10, 8), nullable=True))
    op.add_column("endereco_cliente", sa.Column("longitude", sa.Numeric(11, 8), nullable=True))