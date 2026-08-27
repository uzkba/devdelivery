"""merge heads

Revision ID: a5e00f63f994
Revises: a81b5cb13411, 801b53fe4f8e
Create Date: 2026-08-27 16:15:34.330639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5e00f63f994'
down_revision: Union[str, Sequence[str], None] = ('a81b5cb13411', '801b53fe4f8e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
