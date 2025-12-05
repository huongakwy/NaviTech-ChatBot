"""Change products.images to text array

Revision ID: change_images_to_array_001
Revises: create_products_001
Create Date: 2025-12-05 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "change_images_to_array_001"
down_revision: Union[str, Sequence[str], None] = "create_products_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Alter images column to text[] and convert existing data."""
    op.alter_column(
        "products",
        "images",
        existing_type=sa.Text(),
        type_=postgresql.ARRAY(sa.Text()),
        postgresql_using="string_to_array(images, ',')",
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert images column back to text."""
    op.alter_column(
        "products",
        "images",
        existing_type=postgresql.ARRAY(sa.Text()),
        type_=sa.Text(),
        postgresql_using="array_to_string(images, ',')",
        existing_nullable=True,
    )

