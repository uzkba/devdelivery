"""adiciona indice restaurante_id_criado_em em log_auditoria

Revision ID: 6051fda90f21
Revises: ca5b601cc39d
Create Date: 2026-08-27 16:27:09.447769

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6051fda90f21'
down_revision: Union[str, Sequence[str], None] = 'ca5b601cc39d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_log_auditoria_restaurante_periodo",
        "log_auditoria",
        ["restaurante_id", "criado_em"],
    )


def downgrade() -> None:
    op.drop_index("idx_log_auditoria_restaurante_periodo", table_name="log_auditoria")