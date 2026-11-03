"""fase 2: alimento.categoria_id opcional + CHECK de ao menos uma categoria

Revision ID: f4d3e9f20004
Revises: f3c2d8e10003
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f4d3e9f20004"
down_revision = "f3c2d8e10003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "alimento",
        "categoria_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_alimento_tem_categoria",
        "alimento",
        "categoria_id IS NOT NULL OR categoria_composicao_id IS NOT NULL OR categoria_venda_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_alimento_tem_categoria", "alimento", type_="check")
    # alimento avulso puro não tem categoria_id: preenche a partir das novas colunas
    op.execute(
        "UPDATE alimento "
        "SET categoria_id = COALESCE(categoria_composicao_id, categoria_venda_id) "
        "WHERE categoria_id IS NULL"
    )
    op.alter_column(
        "alimento",
        "categoria_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )