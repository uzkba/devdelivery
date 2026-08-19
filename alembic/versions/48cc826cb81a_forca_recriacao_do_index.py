"""forca recriacao do index

Revision ID: 48cc826cb81a
Revises: ec665c0444a7
Create Date: 2026-08-19 01:19:43.261194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48cc826cb81a'
down_revision: Union[str, Sequence[str], None] = 'ec665c0444a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Criamos o índice na marra usando SQL puro
    op.execute("""
        CREATE UNIQUE INDEX uq_endereco_principal_por_cliente_v2 
        ON endereco_cliente (cliente_id) 
        WHERE endereco_principal = true;
    """)


def downgrade() -> None:
    # Instrução para caso precisemos reverter
    op.execute("DROP INDEX uq_endereco_principal_por_cliente_v2;")
