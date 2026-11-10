"""tipo de atendimento (entrega ou retirada) no pedido; endereco do pedido passa a ser opcional

Revision ID: fe6f3c9d0014
Revises: fd5e2b8c0013
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "fe6f3c9d0014"
down_revision = "fd5e2b8c0013"
branch_labels = None
depends_on = None

tipo_atendimento_pedido = postgresql.ENUM(
    "ENTREGA",
    "RETIRADA",
    name="tipo_atendimento_pedido",
    create_type=False,
)

CHECK_NOME = "ck_pedido_endereco_entrega"
CHECK_SQL = (
    "tipo_atendimento = 'RETIRADA' OR "
    "(endereco_rua IS NOT NULL AND endereco_numero IS NOT NULL AND endereco_bairro IS NOT NULL)"
)


def upgrade() -> None:
    tipo_atendimento_pedido.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "pedido",
        sa.Column(
            "tipo_atendimento",
            tipo_atendimento_pedido,
            nullable=False,
            server_default="ENTREGA",
        ),
    )
    op.alter_column("pedido", "endereco_rua", existing_type=sa.String(150), nullable=True)
    op.alter_column("pedido", "endereco_numero", existing_type=sa.String(20), nullable=True)
    op.alter_column("pedido", "endereco_bairro", existing_type=sa.String(100), nullable=True)
    op.create_check_constraint(CHECK_NOME, "pedido", CHECK_SQL)


def downgrade() -> None:
    op.drop_constraint(CHECK_NOME, "pedido", type_="check")
    # Pedidos de retirada nao tem endereco: o schema antigo exige texto, entao viram vazio.
    for coluna in ("endereco_rua", "endereco_numero", "endereco_bairro"):
        op.execute(f"UPDATE pedido SET {coluna} = '' WHERE {coluna} IS NULL")
    op.alter_column("pedido", "endereco_bairro", existing_type=sa.String(100), nullable=False)
    op.alter_column("pedido", "endereco_numero", existing_type=sa.String(20), nullable=False)
    op.alter_column("pedido", "endereco_rua", existing_type=sa.String(150), nullable=False)
    op.drop_column("pedido", "tipo_atendimento")
    tipo_atendimento_pedido.drop(op.get_bind(), checkfirst=True)