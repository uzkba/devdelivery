"""Etapa 1: disponibilidade, produto avulso, convite, horario, snapshot de pedido

Revision ID: f2b1a7c90002
Revises: f1a0c0de0001
Create Date: 2026-10-31

MIGRATION ADITIVA E REVERSIVEL: nao apaga nenhuma tabela nem coluna existente.
O legado (cardapio, complementos, pagamento, colunas antigas de alimento)
continua no banco e sera removido por migrations proprias, fase a fase.

  1. restaurante: endereco (rua, numero, bairro, cidade)
  2. tabelas novas: horario_atendimento, convite_usuario
  3. alimento: categoria_composicao_id, categoria_venda_id, vendavel_avulso,
     preco_avulso, destaque, imagem_url (dados antigos copiados)
  4. pedido_item: marmita_id, combo_id, snapshot_json
  5. tabelas novas de disponibilidade (regra, regra_dia, excecao)
  6. delivery_rules -> regra_entrega_distancia (nomes em portugues)
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f2b1a7c90002"
down_revision = "f1a0c0de0001"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _id():
    return sa.Column("id", UUID, primary_key=True)


def _ts_columns():
    return [
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # 1) restaurante: endereco
    op.add_column("restaurante", sa.Column("rua", sa.String(150)))
    op.add_column("restaurante", sa.Column("numero", sa.String(20)))
    op.add_column("restaurante", sa.Column("bairro", sa.String(100)))
    op.add_column("restaurante", sa.Column("cidade", sa.String(100)))

    # 2) horario_atendimento e convite_usuario
    op.create_table(
        "horario_atendimento",
        _id(),
        sa.Column("restaurante_id", UUID, sa.ForeignKey("restaurante.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dia_semana", sa.Integer, nullable=False),
        sa.Column("abre_as", sa.Time, nullable=False),
        sa.Column("fecha_as", sa.Time, nullable=False),
        sa.CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_horario_atendimento_dia"),
        sa.UniqueConstraint("restaurante_id", "dia_semana", "abre_as", name="uq_horario_atendimento_faixa"),
    )
    op.create_table(
        "convite_usuario",
        _id(),
        sa.Column("restaurante_id", UUID, sa.ForeignKey("restaurante.id"), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("papel", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_em", sa.DateTime(timezone=True)),
        sa.Column("criado_por", UUID, sa.ForeignKey("usuario_admin.id"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("papel IN ('atendente','caixa')", name="ck_convite_usuario_papel"),
    )
    op.create_index("idx_convite_usuario_restaurante", "convite_usuario", ["restaurante_id", "email"])

    # 3) alimento: dupla natureza (colunas antigas permanecem)
    op.add_column("alimento", sa.Column("categoria_composicao_id", UUID, sa.ForeignKey("categoria_alimento.id")))
    op.add_column("alimento", sa.Column("categoria_venda_id", UUID, sa.ForeignKey("categoria_alimento.id")))
    op.add_column("alimento", sa.Column("vendavel_avulso", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("alimento", sa.Column("preco_avulso", sa.Numeric(10, 2)))
    op.add_column("alimento", sa.Column("destaque", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("alimento", sa.Column("imagem_url", sa.String(500)))
    # Todas as categorias atuais sao de composicao (default da Fase 1). O preco
    # antigo (0 = sem preco) vira preco_avulso, mas nenhum alimento vira
    # "vendavel avulso" sozinho: o restaurante decide isso no admin.
    op.execute(
        "UPDATE alimento SET categoria_composicao_id = categoria_id, "
        "preco_avulso = NULLIF(preco_base, 0)"
    )
    op.create_check_constraint(
        "ck_alimento_avulso_completo",
        "alimento",
        "NOT vendavel_avulso OR (preco_avulso IS NOT NULL AND categoria_venda_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_alimento_preco_avulso", "alimento", "preco_avulso IS NULL OR preco_avulso >= 0"
    )
    op.create_index("idx_alimento_categoria_composicao", "alimento", ["categoria_composicao_id"])
    op.create_index("idx_alimento_categoria_venda", "alimento", ["categoria_venda_id"])

    # 4) pedido_item: ponteiros para marmita/combo + snapshot
    op.add_column("pedido_item", sa.Column("marmita_id", UUID, sa.ForeignKey("marmita.id", ondelete="RESTRICT")))
    op.add_column("pedido_item", sa.Column("combo_id", UUID, sa.ForeignKey("combo.id", ondelete="RESTRICT")))
    op.add_column("pedido_item", sa.Column("snapshot_json", postgresql.JSONB))
    op.create_check_constraint(
        "ck_pedido_item_um_item",
        "pedido_item",
        "num_nonnulls(alimento_id, marmita_id, combo_id) <= 1",
    )
    op.create_index("idx_pedido_item_alimento", "pedido_item", ["alimento_id"])
    op.create_index("idx_pedido_item_marmita", "pedido_item", ["marmita_id"])
    op.create_index("idx_pedido_item_combo", "pedido_item", ["combo_id"])

    # 5) disponibilidade
    op.create_table(
        "disponibilidade_regra",
        _id(),
        sa.Column("marmita_id", UUID, sa.ForeignKey("marmita.id", ondelete="CASCADE")),
        sa.Column("combo_id", UUID, sa.ForeignKey("combo.id", ondelete="CASCADE")),
        sa.Column("alimento_id", UUID, sa.ForeignKey("alimento.id", ondelete="CASCADE")),
        sa.Column("modo", sa.String(20), nullable=False, server_default="TODOS_OS_DIAS"),
        *_ts_columns(),
        sa.CheckConstraint("num_nonnulls(marmita_id, combo_id, alimento_id) = 1", name="ck_disponibilidade_regra_alvo"),
        sa.CheckConstraint("modo IN ('TODOS_OS_DIAS', 'PERSONALIZADO')", name="ck_disponibilidade_regra_modo"),
        sa.UniqueConstraint("marmita_id", name="uq_disponibilidade_regra_marmita"),
        sa.UniqueConstraint("combo_id", name="uq_disponibilidade_regra_combo"),
        sa.UniqueConstraint("alimento_id", name="uq_disponibilidade_regra_alimento"),
    )
    op.create_table(
        "disponibilidade_regra_dia",
        _id(),
        sa.Column("regra_id", UUID, sa.ForeignKey("disponibilidade_regra.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dia_semana", sa.Integer, nullable=False),
        sa.UniqueConstraint("regra_id", "dia_semana", name="uq_disponibilidade_regra_dia"),
        sa.CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_disponibilidade_regra_dia_semana"),
    )
    op.create_table(
        "excecao_disponibilidade",
        _id(),
        sa.Column("marmita_id", UUID, sa.ForeignKey("marmita.id", ondelete="CASCADE")),
        sa.Column("combo_id", UUID, sa.ForeignKey("combo.id", ondelete="CASCADE")),
        sa.Column("alimento_id", UUID, sa.ForeignKey("alimento.id", ondelete="CASCADE")),
        sa.Column("data", sa.Date, nullable=False),
        sa.Column("disponivel", sa.Boolean, nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("num_nonnulls(marmita_id, combo_id, alimento_id) = 1", name="ck_excecao_disponibilidade_alvo"),
        sa.UniqueConstraint("marmita_id", "data", name="uq_excecao_disponibilidade_marmita"),
        sa.UniqueConstraint("combo_id", "data", name="uq_excecao_disponibilidade_combo"),
        sa.UniqueConstraint("alimento_id", "data", name="uq_excecao_disponibilidade_alimento"),
    )

    # 6) delivery_rules -> regra_entrega_distancia (convencao do projeto).
    #    O codigo acessa por atributo (DeliveryRule.fee etc.), que nao muda.
    op.rename_table("delivery_rules", "regra_entrega_distancia")
    op.alter_column("regra_entrega_distancia", "restaurant_id", new_column_name="restaurante_id")
    op.alter_column("regra_entrega_distancia", "min_distance_km", new_column_name="distancia_min_km")
    op.alter_column("regra_entrega_distancia", "max_distance_km", new_column_name="distancia_max_km")
    op.alter_column("regra_entrega_distancia", "fee", new_column_name="taxa")
    op.alter_column("regra_entrega_distancia", "is_active", new_column_name="ativo")
    op.execute("UPDATE regra_entrega_distancia SET ativo = true WHERE ativo IS NULL")
    op.alter_column("regra_entrega_distancia", "ativo", existing_type=sa.Boolean(), nullable=False)
    op.create_index(
        "ix_regra_entrega_distancia_restaurante_id", "regra_entrega_distancia", ["restaurante_id"]
    )


def downgrade() -> None:
    # 6) regra de distancia
    op.drop_index("ix_regra_entrega_distancia_restaurante_id", table_name="regra_entrega_distancia")
    op.alter_column("regra_entrega_distancia", "ativo", existing_type=sa.Boolean(), nullable=True)
    op.alter_column("regra_entrega_distancia", "ativo", new_column_name="is_active")
    op.alter_column("regra_entrega_distancia", "taxa", new_column_name="fee")
    op.alter_column("regra_entrega_distancia", "distancia_max_km", new_column_name="max_distance_km")
    op.alter_column("regra_entrega_distancia", "distancia_min_km", new_column_name="min_distance_km")
    op.alter_column("regra_entrega_distancia", "restaurante_id", new_column_name="restaurant_id")
    op.rename_table("regra_entrega_distancia", "delivery_rules")

    # 5) disponibilidade
    op.drop_table("excecao_disponibilidade")
    op.drop_table("disponibilidade_regra_dia")
    op.drop_table("disponibilidade_regra")

    # 4) pedido_item
    op.drop_index("idx_pedido_item_combo", table_name="pedido_item")
    op.drop_index("idx_pedido_item_marmita", table_name="pedido_item")
    op.drop_index("idx_pedido_item_alimento", table_name="pedido_item")
    op.drop_constraint("ck_pedido_item_um_item", "pedido_item", type_="check")
    op.drop_column("pedido_item", "snapshot_json")
    op.drop_column("pedido_item", "combo_id")
    op.drop_column("pedido_item", "marmita_id")

    # 3) alimento (as colunas antigas nunca foram tocadas)
    op.drop_index("idx_alimento_categoria_venda", table_name="alimento")
    op.drop_index("idx_alimento_categoria_composicao", table_name="alimento")
    op.drop_constraint("ck_alimento_preco_avulso", "alimento", type_="check")
    op.drop_constraint("ck_alimento_avulso_completo", "alimento", type_="check")
    op.drop_column("alimento", "imagem_url")
    op.drop_column("alimento", "destaque")
    op.drop_column("alimento", "preco_avulso")
    op.drop_column("alimento", "vendavel_avulso")
    op.drop_column("alimento", "categoria_venda_id")
    op.drop_column("alimento", "categoria_composicao_id")

    # 2) tabelas novas
    op.drop_table("convite_usuario")
    op.drop_table("horario_atendimento")

    # 1) restaurante
    op.drop_column("restaurante", "cidade")
    op.drop_column("restaurante", "bairro")
    op.drop_column("restaurante", "numero")
    op.drop_column("restaurante", "rua")
