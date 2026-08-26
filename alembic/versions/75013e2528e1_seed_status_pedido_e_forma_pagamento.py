"""seed status_pedido e forma_pagamento

Revision ID: 75013e2528e1
Revises: 7d2e5abb343e
Create Date: 2026-08-24 22:29:47.805514

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75013e2528e1'
down_revision: Union[str, Sequence[str], None] = '7d2e5abb343e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


status_pedido = sa.table(
    "status_pedido",
    sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
    sa.column("codigo", sa.String),
    sa.column("nome", sa.String),
    sa.column("ordem", sa.Integer),
    sa.column("is_final", sa.Boolean),
)

forma_pagamento = sa.table(
    "forma_pagamento",
    sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
    sa.column("codigo", sa.String),
    sa.column("nome", sa.String),
    sa.column("ativo", sa.Boolean),
)

STATUS_SEED = [
    {"codigo": "CRIADO", "nome": "Criado", "ordem": 1, "is_final": False},
    {"codigo": "CONFIRMADO", "nome": "Confirmado", "ordem": 2, "is_final": False},
    {"codigo": "EM_PREPARO", "nome": "Em preparo", "ordem": 3, "is_final": False},
    {"codigo": "SAIU_PARA_ENTREGA", "nome": "Saiu para entrega", "ordem": 4, "is_final": False},
    {"codigo": "ENTREGUE", "nome": "Entregue", "ordem": 5, "is_final": True},
    {"codigo": "CANCELADO", "nome": "Cancelado", "ordem": 6, "is_final": True},
]

FORMA_PAGAMENTO_SEED = [
    {"codigo": "DINHEIRO", "nome": "Dinheiro"},
    {"codigo": "PIX", "nome": "Pix"},
    {"codigo": "CARTAO_CREDITO", "nome": "Cartão de Crédito"},
    {"codigo": "CARTAO_DEBITO", "nome": "Cartão de Débito"},
]


def upgrade():
    op.bulk_insert(
        status_pedido,
        [{"id": uuid.uuid4(), **row} for row in STATUS_SEED],
    )
    op.bulk_insert(
        forma_pagamento,
        [{"id": uuid.uuid4(), "ativo": True, **row} for row in FORMA_PAGAMENTO_SEED],
    )


def downgrade():
    op.execute(
        status_pedido.delete().where(
            status_pedido.c.codigo.in_([s["codigo"] for s in STATUS_SEED])
        )
    )
    op.execute(
        forma_pagamento.delete().where(
            forma_pagamento.c.codigo.in_([f["codigo"] for f in FORMA_PAGAMENTO_SEED])
        )
    )