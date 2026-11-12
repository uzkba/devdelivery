from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f1b3c8d90016"
down_revision = "ff7a4d0e0015"
branch_labels = None
depends_on = None


def _uuid():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.execute(
        "UPDATE alimento SET categoria_composicao_id = categoria_id "
        "WHERE categoria_composicao_id IS NULL AND categoria_id IS NOT NULL"
    )
    op.drop_constraint("ck_alimento_tem_categoria", "alimento", type_="check")
    op.create_check_constraint(
        "ck_alimento_tem_categoria",
        "alimento",
        "categoria_composicao_id IS NOT NULL OR categoria_venda_id IS NOT NULL",
    )

    op.drop_table("pedido_item_opcao")
    op.drop_table("opcao_complemento")
    op.drop_table("grupo_complemento")
    op.drop_table("cardapio_item")
    op.drop_table("cardapio")

    op.drop_constraint("ck_alimento_preco_base_positivo", "alimento", type_="check")
    op.drop_column("alimento", "categoria_id")
    op.drop_column("alimento", "preco_base")
    op.drop_column("alimento", "disponivel")
    op.drop_column("categoria_alimento", "prato_principal")


def downgrade() -> None:
    op.add_column(
        "categoria_alimento",
        sa.Column("prato_principal", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "alimento",
        sa.Column("disponivel", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "alimento",
        sa.Column("preco_base", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "alimento",
        sa.Column("categoria_id", _uuid(), sa.ForeignKey("categoria_alimento.id"), nullable=True),
    )
    op.alter_column("alimento", "disponivel", server_default=None)
    op.alter_column("alimento", "preco_base", server_default=None)

    op.execute("UPDATE alimento SET categoria_id = categoria_composicao_id")
    op.create_check_constraint("ck_alimento_preco_base_positivo", "alimento", "preco_base >= 0")
    op.drop_constraint("ck_alimento_tem_categoria", "alimento", type_="check")
    op.create_check_constraint(
        "ck_alimento_tem_categoria",
        "alimento",
        "categoria_id IS NOT NULL OR categoria_composicao_id IS NOT NULL "
        "OR categoria_venda_id IS NOT NULL",
    )

    op.create_table(
        "cardapio",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("restaurante_id", _uuid(), sa.ForeignKey("restaurante.id"), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("criado_por", _uuid(), sa.ForeignKey("usuario_admin.id"), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("restaurante_id", "data"),
    )
    op.create_table(
        "cardapio_item",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column(
            "cardapio_id", _uuid(), sa.ForeignKey("cardapio.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("alimento_id", _uuid(), sa.ForeignKey("alimento.id"), nullable=False),
        sa.Column("disponivel", sa.Boolean(), nullable=False),
        sa.Column("preco_dia", sa.Numeric(10, 2), nullable=True),
        sa.UniqueConstraint("cardapio_id", "alimento_id", name="uq_cardapio_item_alimento"),
        sa.CheckConstraint("preco_dia IS NULL OR preco_dia >= 0", name="ck_cardapio_item_preco_dia"),
    )
    op.create_index(
        "idx_cardapio_item_disponivel", "cardapio_item", ["cardapio_id", "disponivel"]
    )
    op.create_table(
        "grupo_complemento",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column(
            "alimento_id", _uuid(), sa.ForeignKey("alimento.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("nome", sa.String(60), nullable=False),
        sa.Column("escolhas_minimas", sa.Integer(), nullable=False),
        sa.Column("escolhas_maximas", sa.Integer(), nullable=False),
        sa.Column("ordem_exibicao", sa.Integer(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "escolhas_maximas >= escolhas_minimas", name="ck_grupo_complemento_limites"
        ),
    )
    op.create_table(
        "opcao_complemento",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column(
            "grupo_id",
            _uuid(),
            sa.ForeignKey("grupo_complemento.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(60), nullable=False),
        sa.Column("preco_adicional", sa.Numeric(10, 2), nullable=False),
        sa.Column("disponivel", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "pedido_item_opcao",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column(
            "pedido_item_id",
            _uuid(),
            sa.ForeignKey("pedido_item.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opcao_complemento_id",
            _uuid(),
            sa.ForeignKey("opcao_complemento.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("nome_opcao", sa.String(60), nullable=False),
        sa.Column("preco_adicional_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantidade > 0", name="ck_pedido_item_opcao_quantidade"),
        sa.CheckConstraint(
            "preco_adicional_unitario >= 0", name="ck_pedido_item_opcao_preco"
        ),
    )