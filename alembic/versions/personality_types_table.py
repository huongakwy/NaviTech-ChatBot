"""create personality_types table

Revision ID: personality_001
Revises: a01262051880
Create Date: 2025-10-25 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'personality_001'
down_revision: Union[str, Sequence[str], None] = 'a01262051880'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create personality_types table
    op.create_table(
        "personality_types",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Insert default personality
    op.execute(
        "INSERT INTO personality_types (name, description) VALUES ('bình_thường', 'Bình thường, chuyên nghiệp, cân bằng')"
    )


def downgrade() -> None:
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if table exists before dropping
    if 'personality_types' in inspector.get_table_names():
        op.drop_table("personality_types")
