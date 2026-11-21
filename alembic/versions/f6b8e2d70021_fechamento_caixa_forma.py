import sqlalchemy as sa
from alembic import op

revision = "f6b8e2d70021"
down_revision = "f5a7d1c60020"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fechamento_caixa_forma",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("fechamento_id", sa.UUID(), nullable=False),
        sa.Column("forma", sa.String(length=20), nullable=False),
        sa.Column("quantidade_pedidos", sa.Integer(), nullable=False),
        sa.Column("valor_esperado", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("valor_contado", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("diferenca", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.CheckConstraint("valor_contado >= 0", name="ck_fechamento_forma_contado"),
        sa.ForeignKeyConstraint(
            ["fechamento_id"],
            ["fechamento_caixa.id"],
            name="fk_fechamento_forma_fechamento",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fechamento_id", "forma", name="uq_fechamento_forma"),
    )


def downgrade():
    op.drop_table("fechamento_caixa_forma")