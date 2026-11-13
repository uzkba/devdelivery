import sqlalchemy as sa
from alembic import op

revision = "f3d5b9a40018"
down_revision = "f2c4a8e30017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pedido", sa.Column("motivo_status", sa.String(300), nullable=True))
    op.add_column("pedido", sa.Column("entregador_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_pedido_entregador",
        "pedido",
        "usuario_admin",
        ["entregador_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_pedido_entregador", "pedido", ["entregador_id"])


def downgrade():
    op.drop_index("idx_pedido_entregador", table_name="pedido")
    op.drop_constraint("fk_pedido_entregador", "pedido", type_="foreignkey")
    op.drop_column("pedido", "entregador_id")
    op.drop_column("pedido", "motivo_status")