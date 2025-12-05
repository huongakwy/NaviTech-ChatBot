"""add ai_personality to users table

Revision ID: add_ai_personality_001
Revises: personality_001
Create Date: 2025-10-25 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_ai_personality_001'
down_revision: Union[str, Sequence[str], None] = 'personality_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ai_personality_id column with FK to personality_types
    op.add_column(
        "users",
        sa.Column(
            "ai_personality_id",
            sa.Integer,
            sa.ForeignKey("personality_types.id", ondelete="SET NULL"),
            nullable=True
        ),
    )


def downgrade() -> None:
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if table exists
    if 'users' not in inspector.get_table_names():
        return
    
    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Drop column if it exists
    if 'ai_personality_id' in existing_columns:
        op.drop_column("users", "ai_personality_id")
