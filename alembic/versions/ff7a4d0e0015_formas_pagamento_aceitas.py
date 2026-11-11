"""formas de pagamento aceitas por restaurante

Revision ID: ff7a4d0e0015
Revises: fe6f3c9d0014
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ff7a4d0e0015"
down_revision = "fe6f3c9d0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "restaurante_forma_pagamento",
        sa.Column(
            "restaurante_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("restaurante.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "forma_pagamento_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("forma_pagamento.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
    # Restaurantes existentes passam a aceitar todas as formas ativas (o comportamento de hoje).
    op.execute(
        "INSERT INTO restaurante_forma_pagamento (restaurante_id, forma_pagamento_id) "
        "SELECT r.id, f.id FROM restaurante r CROSS JOIN forma_pagamento f WHERE f.ativo"
    )


def downgrade() -> None:
    op.drop_table("restaurante_forma_pagamento")