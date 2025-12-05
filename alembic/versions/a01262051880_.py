"""empty message

Revision ID: a01262051880
Revises: 3572feb401d9
Create Date: 2025-10-22 20:42:23.517461

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a01262051880'
down_revision: Union[str, Sequence[str], None] = '3572feb401d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
