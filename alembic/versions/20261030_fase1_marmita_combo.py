"""Fase 1: marmita, combo e tipo de categoria de alimento

Revision ID: f1a0c0de0001
Revises: REPLACE_WITH_CURRENT_HEAD
Create Date: 2026-10-30

AJUSTE: troque `down_revision` pelo resultado de `alembic heads`.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f1a0c0de0001"
down_revision = "6613ee3023d9"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)

tipo_marmita = postgresql.ENUM(
    "PERSONALIZAVEL", "PRONTA", name="tipo_marmita", create_type=False
)


def _id():
    return sa.Column("id", UUID, primary_key=True)


def _ts_columns():
    return [
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()

    # 1) RN-C01: categoria de composicao x categoria de venda avulsa.
    #    Idempotente. As categorias atuais sao todas de composicao (default).
    cols = {c["name"] for c in sa.inspect(bind).get_columns("categoria_alimento")}
    if "tipo" not in cols:
        op.add_column(
            "categoria_alimento",
            sa.Column("tipo", sa.String(20), nullable=False, server_default="composicao"),
        )
        op.create_check_constraint(
            "ck_categoria_alimento_tipo",
            "categoria_alimento",
            "tipo IN ('composicao', 'venda')",
        )

    tipo_marmita.create(bind, checkfirst=True)

    # 2) marmita
    op.create_table(
        "marmita",
        _id(),
        sa.Column("restaurante_id", UUID, sa.ForeignKey("restaurante.id"), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("descricao", sa.String(500)),
        sa.Column("tipo", tipo_marmita, nullable=False),
        sa.Column("tamanho", sa.String(40)),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("destaque", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("imagem_url", sa.String(500)),
        sa.Column("calorias_kcal", sa.Integer),
        sa.Column("proteina_g", sa.Numeric(6, 1)),
        sa.Column("carboidrato_g", sa.Numeric(6, 1)),
        sa.Column("gordura_g", sa.Numeric(6, 1)),
        *_ts_columns(),
        sa.CheckConstraint("preco >= 0", name="ck_marmita_preco"),
        sa.CheckConstraint("calorias_kcal IS NULL OR calorias_kcal >= 0", name="ck_marmita_calorias"),
        sa.CheckConstraint(
            "(proteina_g IS NULL OR proteina_g >= 0) AND "
            "(carboidrato_g IS NULL OR carboidrato_g >= 0) AND "
            "(gordura_g IS NULL OR gordura_g >= 0)",
            name="ck_marmita_macros",
        ),
    )
    op.create_index("idx_marmita_restaurante_ativo", "marmita", ["restaurante_id", "ativo"])

    # 3) marmita_categoria (PERSONALIZAVEL)
    op.create_table(
        "marmita_categoria",
        _id(),
        sa.Column("marmita_id", UUID, sa.ForeignKey("marmita.id", ondelete="CASCADE"), nullable=False),
        sa.Column("categoria_alimento_id", UUID, sa.ForeignKey("categoria_alimento.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantidade_exigida", sa.Integer, nullable=False),
        sa.Column("posicao", sa.Integer, nullable=False),
        sa.UniqueConstraint("marmita_id", "categoria_alimento_id", name="uq_marmita_categoria"),
        sa.CheckConstraint("quantidade_exigida >= 0", name="ck_marmita_categoria_quantidade"),
    )
    op.create_index("idx_marmita_categoria_categoria", "marmita_categoria", ["categoria_alimento_id"])

    # 4) marmita_composicao (PRONTA)
    op.create_table(
        "marmita_composicao",
        _id(),
        sa.Column("marmita_id", UUID, sa.ForeignKey("marmita.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alimento_id", UUID, sa.ForeignKey("alimento.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantidade_fixa", sa.Integer, nullable=False),
        sa.Column("posicao", sa.Integer, nullable=False),
        sa.UniqueConstraint("marmita_id", "alimento_id", name="uq_marmita_composicao"),
        sa.CheckConstraint("quantidade_fixa >= 1", name="ck_marmita_composicao_quantidade"),
    )
    op.create_index("idx_marmita_composicao_alimento", "marmita_composicao", ["alimento_id"])

    # 5) combo
    op.create_table(
        "combo",
        _id(),
        sa.Column("restaurante_id", UUID, sa.ForeignKey("restaurante.id"), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("descricao", sa.String(500)),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("destaque", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("imagem_url", sa.String(500)),
        *_ts_columns(),
        sa.CheckConstraint("preco >= 0", name="ck_combo_preco"),
    )
    op.create_index("idx_combo_restaurante_ativo", "combo", ["restaurante_id", "ativo"])

    # 6) combo_item_marmita / combo_item_alimento
    op.create_table(
        "combo_item_marmita",
        _id(),
        sa.Column("combo_id", UUID, sa.ForeignKey("combo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("marmita_id", UUID, sa.ForeignKey("marmita.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantidade", sa.Integer, nullable=False),
        sa.Column("posicao", sa.Integer, nullable=False),
        sa.UniqueConstraint("combo_id", "marmita_id", name="uq_combo_item_marmita"),
        sa.CheckConstraint("quantidade >= 1", name="ck_combo_item_marmita_quantidade"),
    )
    op.create_index("idx_combo_item_marmita_marmita", "combo_item_marmita", ["marmita_id"])

    op.create_table(
        "combo_item_alimento",
        _id(),
        sa.Column("combo_id", UUID, sa.ForeignKey("combo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alimento_id", UUID, sa.ForeignKey("alimento.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantidade", sa.Integer, nullable=False),
        sa.Column("posicao", sa.Integer, nullable=False),
        sa.UniqueConstraint("combo_id", "alimento_id", name="uq_combo_item_alimento"),
        sa.CheckConstraint("quantidade >= 1", name="ck_combo_item_alimento_quantidade"),
    )
    op.create_index("idx_combo_item_alimento_alimento", "combo_item_alimento", ["alimento_id"])


def downgrade() -> None:
    op.drop_table("combo_item_alimento")
    op.drop_table("combo_item_marmita")
    op.drop_table("combo")
    op.drop_table("marmita_composicao")
    op.drop_table("marmita_categoria")
    op.drop_table("marmita")
    tipo_marmita.drop(op.get_bind(), checkfirst=True)
    # A coluna categoria_alimento.tipo e aditiva e inofensiva: fica no downgrade.
