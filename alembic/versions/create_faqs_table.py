"""Create FAQs table

Revision ID: create_faqs_001
Revises: create_products_001
Create Date: 2026-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_faqs_001'
down_revision: Union[str, Sequence[str], None] = 'change_images_to_array_fix_002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create faqs table với indexes"""
    from sqlalchemy import inspect
    
    # Get connection and check if table exists
    conn = op.get_bind()
    inspector = inspect(conn)
    table_exists = 'faqs' in inspector.get_table_names()
    
    # Only create table if it doesn't exist
    if not table_exists:
        op.create_table(
            'faqs',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column('question', sa.Text, nullable=False),
            sa.Column('answer', sa.Text, nullable=False),
            sa.Column('category', sa.String(100), nullable=True, index=True),
            sa.Column('priority', sa.Integer, server_default='0', nullable=False),
            sa.Column('is_active', sa.Boolean, server_default='true', nullable=False, index=True),
            sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp(), nullable=False),
            sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp(), nullable=False),
        )
        
        # Create indexes
        op.create_index('idx_faqs_user_active', 'faqs', ['user_id', 'is_active'])
        op.create_index('idx_faqs_category', 'faqs', ['category'])
        op.create_index('idx_faqs_priority', 'faqs', ['priority'])
        
        print("✅ FAQs table created successfully")
    else:
        print("ℹ️  FAQs table already exists, skipping creation")


def downgrade() -> None:
    """Drop faqs table"""
    op.drop_table('faqs')
    print("✅ FAQs table dropped")
