"""merge heads

Revision ID: 2d8ea3db7e19
Revises: 6051fda90f21, 7095ca893dea
Create Date: 2026-08-27 17:10:39.627471

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d8ea3db7e19'
down_revision: Union[str, Sequence[str], None] = ('6051fda90f21', '7095ca893dea')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
