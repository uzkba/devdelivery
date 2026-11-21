import sqlalchemy as sa
from alembic import op

revision = "f5a7d1c60020"
down_revision = "f4e6c0b50019"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "caixa_dia",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("restaurante_id", sa.UUID(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=10), server_default="ABERTO", nullable=False),
        sa.Column("aberto_por", sa.UUID(), nullable=False),
        sa.Column("aberto_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("fechado_por", sa.UUID(), nullable=True),
        sa.Column("fechado_em", sa.DateTime(), nullable=True),
        sa.Column("reaberto_por", sa.UUID(), nullable=True),
        sa.Column("reaberto_em", sa.DateTime(), nullable=True),
        sa.Column("reaberturas", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fechamento_id", sa.UUID(), nullable=True),
        sa.CheckConstraint("status IN ('ABERTO','FECHADO')", name="ck_caixa_dia_status"),
        sa.CheckConstraint("reaberturas >= 0", name="ck_caixa_dia_reaberturas"),
        sa.ForeignKeyConstraint(["restaurante_id"], ["restaurante.id"]),
        sa.ForeignKeyConstraint(["aberto_por"], ["usuario_admin.id"]),
        sa.ForeignKeyConstraint(["fechado_por"], ["usuario_admin.id"]),
        sa.ForeignKeyConstraint(["reaberto_por"], ["usuario_admin.id"]),
        sa.ForeignKeyConstraint(
            ["fechamento_id"], ["fechamento_caixa.id"], name="fk_caixa_dia_fechamento", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurante_id", "data", name="uq_caixa_dia_restaurante_data"),
    )
    op.create_index("idx_caixa_dia_restaurante_status", "caixa_dia", ["restaurante_id", "status"])


def downgrade():
    op.drop_index("idx_caixa_dia_restaurante_status", table_name="caixa_dia")
    op.drop_table("caixa_dia")