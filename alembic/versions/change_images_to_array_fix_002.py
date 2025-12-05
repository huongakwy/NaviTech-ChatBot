"""Ensure products.images is text[]

Revision ID: change_images_to_array_fix_002
Revises: change_images_to_array_001
Create Date: 2025-12-05 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "change_images_to_array_fix_002"
down_revision: Union[str, Sequence[str], None] = "change_images_to_array_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Force products.images to text[].
    Handles existing text values and already-array values.
    """
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'products'
              AND column_name = 'images'
              AND data_type <> 'ARRAY'
          ) THEN
            ALTER TABLE products
              ALTER COLUMN images TYPE text[]
              USING (
                CASE
                  WHEN images IS NULL THEN NULL
                  -- If value already looks like '{a,b}', strip braces then split
                  WHEN images LIKE '{%' THEN string_to_array(trim(both '{}' from images), ',')
                  ELSE string_to_array(images, ',')
                END
              );
          END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """
    Revert images back to text if currently array.
    """
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'products'
              AND column_name = 'images'
              AND data_type = 'ARRAY'
          ) THEN
            ALTER TABLE products
              ALTER COLUMN images TYPE text
              USING array_to_string(images, ',');
          END IF;
        END
        $$;
        """
    )

