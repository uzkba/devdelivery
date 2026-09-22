"""add configuracao_entrega e regra_entrega_bairro

Revision ID: 6613ee3023d9
Revises: bcb1810fd286
Create Date: ...
"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "6613ee3023d9"
down_revision = "bcb1810fd286"
branch_labels = None
depends_on = None

modo_cobranca_entrega = postgresql.ENUM(
    "GRATIS", "FIXO", "BAIRRO", "DISTANCIA",
    name="modo_cobranca_entrega",
    create_type=False,
)


def upgrade() -> None:
    modo_cobranca_entrega.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "configuracao_entrega",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("restaurante_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("restaurante.id"), nullable=False, unique=True),
        sa.Column("entrega_ativa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("retirada_ativa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("valor_minimo", sa.Numeric(10, 2), nullable=True),
        sa.Column("tempo_entrega_min", sa.Integer(), nullable=True),
        sa.Column("tempo_retirada_min", sa.Integer(), nullable=True),
        sa.Column("modo_cobranca", modo_cobranca_entrega, nullable=False),
        sa.Column("taxa_fixa", sa.Numeric(10, 2), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "regra_entrega_bairro",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("restaurante_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("restaurante.id"), nullable=False),
        sa.Column("bairro", sa.String(120), nullable=False),
        sa.Column("taxa", sa.Numeric(10, 2), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_regra_entrega_bairro_restaurante_id", "regra_entrega_bairro", ["restaurante_id"])


def downgrade() -> None:
    op.drop_index("ix_regra_entrega_bairro_restaurante_id", table_name="regra_entrega_bairro")
    op.drop_table("regra_entrega_bairro")
    op.drop_table("configuracao_entrega")
    modo_cobranca_entrega.drop(op.get_bind(), checkfirst=True)