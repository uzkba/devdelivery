"""remove entrega por distancia (tabela regra_entrega_distancia e valor DISTANCIA do enum)

Revision ID: fb2a9d7e0011
Revises: fa0d5c6b0010
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "fb2a9d7e0011"
down_revision = "fa0d5c6b0010"
branch_labels = None
depends_on = None

TIPO = "modo_cobranca_entrega"


def _recriar_enum(valores: list[str]) -> None:
    lista = ", ".join(f"'{valor}'" for valor in valores)
    op.execute(f"ALTER TYPE {TIPO} RENAME TO {TIPO}_antigo")
    op.execute(f"CREATE TYPE {TIPO} AS ENUM ({lista})")
    op.execute(
        f"ALTER TABLE configuracao_entrega ALTER COLUMN modo_cobranca "
        f"TYPE {TIPO} USING modo_cobranca::text::{TIPO}"
    )
    op.execute(f"DROP TYPE {TIPO}_antigo")


def upgrade() -> None:
    op.execute(
        "UPDATE configuracao_entrega SET modo_cobranca = 'GRATIS' "
        "WHERE modo_cobranca::text = 'DISTANCIA'"
    )
    op.drop_table("regra_entrega_distancia")
    _recriar_enum(["GRATIS", "FIXO", "BAIRRO"])


def downgrade() -> None:
    _recriar_enum(["GRATIS", "FIXO", "BAIRRO", "DISTANCIA"])
    op.create_table(
        "regra_entrega_distancia",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "restaurante_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("restaurante.id"),
            nullable=False,
        ),
        sa.Column("distancia_min_km", sa.Numeric(5, 2), nullable=False),
        sa.Column("distancia_max_km", sa.Numeric(5, 2), nullable=False),
        sa.Column("taxa", sa.Numeric(10, 2), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_regra_entrega_distancia_restaurante_id",
        "regra_entrega_distancia",
        ["restaurante_id"],
    )