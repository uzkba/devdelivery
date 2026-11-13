import sqlalchemy as sa
from alembic import op

revision = "f4e6c0b50019"
down_revision = "f3d5b9a40018"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "historico_pagamento_pedido",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("pedido_id", sa.UUID(), nullable=False),
        sa.Column("forma_anterior_id", sa.UUID(), nullable=False),
        sa.Column("forma_nova_id", sa.UUID(), nullable=False),
        sa.Column("usuario_id", sa.UUID(), nullable=False),
        sa.Column("alterado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedido.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["forma_anterior_id"], ["forma_pagamento.id"]),
        sa.ForeignKeyConstraint(["forma_nova_id"], ["forma_pagamento.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario_admin.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_historico_pagamento_pedido",
        "historico_pagamento_pedido",
        ["pedido_id", "alterado_em"],
    )


def downgrade():
    op.drop_index("idx_historico_pagamento_pedido", table_name="historico_pagamento_pedido")
    op.drop_table("historico_pagamento_pedido")