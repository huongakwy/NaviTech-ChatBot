"""Add company_name and agent_name to personality_types

Revision ID: add_company_agent_001
Revises: add_ai_personality_001
Create Date: 2025-10-25 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_company_agent_001'
down_revision: Union[str, Sequence[str], None] = 'add_ai_personality_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add company_name and agent_name columns to personality_types table"""
    op.add_column('personality_types', sa.Column('company_name', sa.String(255), server_default='NAVITECH', nullable=False))
    op.add_column('personality_types', sa.Column('agent_name', sa.String(255), server_default='trợ lý AI', nullable=False))


def downgrade() -> None:
    """Remove company_name and agent_name columns from personality_types table"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if table exists
    if 'personality_types' not in inspector.get_table_names():
        return
    
    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('personality_types')]
    
    # Drop columns if they exist
    if 'agent_name' in existing_columns:
        op.drop_column('personality_types', 'agent_name')
    if 'company_name' in existing_columns:
        op.drop_column('personality_types', 'company_name')
