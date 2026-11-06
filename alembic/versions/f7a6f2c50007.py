"""categoria_alimento: grupo (prato/bebida) na categoria de venda

Revision ID: f7a6f2c50007
Revises: f6f5e1b40006
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "f7a6f2c50007"
down_revision = "f6f5e1b40006"
branch_labels = None
depends_on = None

_PADRAO_BEBIDA = "(bebida|suco|refri|água|agua|cerveja)"


def upgrade() -> None:
    op.add_column("categoria_alimento", sa.Column("grupo", sa.String(length=10), nullable=True))

    # Só categoria de venda tem grupo. Nome que indica bebida vira 'bebida'; o resto, 'prato'.
    op.execute(
        "UPDATE categoria_alimento SET grupo = CASE "
        f"WHEN lower(nome) ~ '{_PADRAO_BEBIDA}' THEN 'bebida' ELSE 'prato' END "
        "WHERE tipo = 'venda'"
    )

    op.create_check_constraint(
        "ck_categoria_alimento_grupo", "categoria_alimento", "grupo IS NULL OR grupo IN ('prato', 'bebida')"
    )
    op.create_check_constraint(
        "ck_categoria_alimento_grupo_tipo", "categoria_alimento", "(tipo = 'venda') = (grupo IS NOT NULL)"
    )


def downgrade() -> None:
    op.drop_constraint("ck_categoria_alimento_grupo_tipo", "categoria_alimento", type_="check")
    op.drop_constraint("ck_categoria_alimento_grupo", "categoria_alimento", type_="check")
    op.drop_column("categoria_alimento", "grupo")