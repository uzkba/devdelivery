import sqlalchemy as sa
from alembic import op

revision = "f7c9f3e80022"
down_revision = "f6b8e2d70021"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fechamento_caixa_entregador",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("fechamento_id", sa.UUID(), nullable=False),
        sa.Column("entregador_id", sa.UUID(), nullable=False),
        sa.Column("entregador_nome", sa.String(length=150), nullable=False),
        sa.Column("quantidade_entregas", sa.Integer(), nullable=False),
        sa.Column("valor_esperado", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("valor_repassado", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("diferenca", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.CheckConstraint("valor_repassado >= 0", name="ck_fechamento_entregador_repassado"),
        sa.ForeignKeyConstraint(
            ["fechamento_id"],
            ["fechamento_caixa.id"],
            name="fk_fechamento_entregador_fechamento",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["entregador_id"], ["usuario_admin.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fechamento_id", "entregador_id", name="uq_fechamento_entregador"),
    )


def downgrade():
    op.drop_table("fechamento_caixa_entregador")