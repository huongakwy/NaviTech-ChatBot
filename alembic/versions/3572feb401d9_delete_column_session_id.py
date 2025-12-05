"""delete column session id

Revision ID: 3572feb401d9
Revises: eca40d3692b4
Create Date: 2025-10-22 08:25:06.938602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3572feb401d9'
down_revision: Union[str, Sequence[str], None] = 'eca40d3692b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Drop session_id column if it exists
    if 'chats' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('chats')]
        if 'session_id' in existing_columns:
            op.drop_column('chats', 'session_id')
    
    # Make phone_number nullable if table exists
    if 'users' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        if 'phone_number' in existing_columns:
            op.alter_column('users', 'phone_number',
                       existing_type=sa.String(),
                       nullable=True)
    

def downgrade() -> None:
    """Downgrade schema."""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Add session_id column to chats if table exists and column doesn't exist
    if 'chats' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('chats')]
        if 'session_id' not in existing_columns:
            op.add_column('chats', sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Update NULL phone_number values before setting NOT NULL constraint
    if 'users' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        if 'phone_number' in existing_columns:
            # Check if column is nullable
            phone_col = next((col for col in inspector.get_columns('users') if col['name'] == 'phone_number'), None)
            if phone_col and phone_col.get('nullable', True):
                # Update NULL values before setting NOT NULL
                op.execute("UPDATE users SET phone_number = '' WHERE phone_number IS NULL")
                op.alter_column('users', 'phone_number',
                           existing_type=sa.String(),
                           nullable=False)
