"""corrige regressao de ativo/descricao em categoria_alimento e adiciona tamanho de marmita, limite por categoria e tamanho no cardapio_item

Revision ID: 8f3a1c9d2b4e
Revises: 25e6120e5580
Create Date: 2026-08-22 00:00:00.000000
"""
import uuid

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8f3a1c9d2b4e"
down_revision = "25e6120e5580"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0. CORREÇÃO DE REGRESSÃO: a migration 25e6120e5580 removeu
    #    'descricao' e 'ativo' de categoria_alimento (provavelmente um
    #    autogenerate feito em cima de um models.py desatualizado, sem
    #    essas colunas). O CRUD de Categoria de Alimento (service) depende
    #    delas para soft-delete e para o filtro apenas_ativas. Restaurando.
    op.add_column("categoria_alimento", sa.Column("descricao", sa.Text(), nullable=True))
    op.add_column(
        "categoria_alimento",
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
    )

    # 1. coluna prato_principal em categoria_alimento
    op.add_column(
        "categoria_alimento",
        sa.Column(
            "prato_principal",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # 2. tabela tamanho_marmita
    op.create_table(
        "tamanho_marmita",
        sa.Column("id", sa.Uuid(), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "restaurante_id",
            sa.Uuid(),
            sa.ForeignKey("restaurante.id"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(length=30), nullable=False),
        sa.Column("ordem_exibicao", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("restaurante_id", "nome", name="uq_tamanho_marmita_restaurante_nome"),
    )

    # 3. tabela limite_categoria_tamanho
    op.create_table(
        "limite_categoria_tamanho",
        sa.Column("id", sa.Uuid(), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "tamanho_id",
            sa.Uuid(),
            sa.ForeignKey("tamanho_marmita.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "categoria_id",
            sa.Uuid(),
            sa.ForeignKey("categoria_alimento.id"),
            nullable=False,
        ),
        sa.Column("quantidade_maxima", sa.Integer(), nullable=False),
        sa.UniqueConstraint("tamanho_id", "categoria_id", name="uq_limite_categoria_tamanho_tamanho_categoria"),
        sa.CheckConstraint("quantidade_maxima >= 0", name="ck_limite_categoria_tamanho_qtd"),
    )

    # 4. coluna tamanho_id em cardapio_item
    op.add_column(
        "cardapio_item",
        sa.Column("tamanho_id", sa.Uuid(), sa.ForeignKey("tamanho_marmita.id"), nullable=True),
    )

    # 5. troca a unique constraint antiga (cardapio_id, alimento_id) pela
    #    nova (cardapio_id, alimento_id, tamanho_id) + índice único parcial
    #    para o caso tamanho_id IS NULL (mesmo padrão do endereco_principal).
    #
    # ATENÇÃO: confirme o nome real da constraint antes de rodar:
    #   SELECT conname FROM pg_constraint WHERE conrelid = 'cardapio_item'::regclass AND contype = 'u';
    op.drop_constraint(
        "cardapio_item_cardapio_id_alimento_id_key",
        "cardapio_item",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_cardapio_item_alimento_tamanho",
        "cardapio_item",
        ["cardapio_id", "alimento_id", "tamanho_id"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cardapio_item_sem_tamanho
        ON cardapio_item (cardapio_id, alimento_id)
        WHERE tamanho_id IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_cardapio_item_sem_tamanho")
    op.drop_constraint("uq_cardapio_item_alimento_tamanho", "cardapio_item", type_="unique")
    op.create_unique_constraint(
        "cardapio_item_cardapio_id_alimento_id_key",
        "cardapio_item",
        ["cardapio_id", "alimento_id"],
    )
    op.drop_column("cardapio_item", "tamanho_id")
    op.drop_table("limite_categoria_tamanho")
    op.drop_table("tamanho_marmita")
    op.drop_column("categoria_alimento", "prato_principal")
    op.drop_column("categoria_alimento", "ativo")
    op.drop_column("categoria_alimento", "descricao")