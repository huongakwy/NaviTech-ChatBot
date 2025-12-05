"""Create products table for AI_crawl

Revision ID: create_products_001
Revises: add_company_agent_001
Create Date: 2025-12-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_products_001'
down_revision: Union[str, Sequence[str], None] = 'add_company_agent_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create products table with all indexes"""
    from sqlalchemy import inspect
    
    # Get connection and check if table exists
    conn = op.get_bind()
    inspector = inspect(conn)
    table_exists = 'products' in inspector.get_table_names()
    
    # Only create table if it doesn't exist
    if not table_exists:
        op.create_table(
            'products',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('website_id', sa.Integer, server_default='0', nullable=True),
            sa.Column('website_name', sa.String(255), nullable=True),
            sa.Column('url', sa.String(1000), nullable=False, unique=True),
            sa.Column('title', sa.String(500), nullable=True),
            sa.Column('price', sa.Float, server_default='0', nullable=True),
            sa.Column('original_price', sa.Float, server_default='0', nullable=True),
            sa.Column('currency', sa.String(10), server_default='VND', nullable=True),
            sa.Column('sku', sa.String(255), nullable=True),
            sa.Column('brand', sa.String(255), nullable=True),
            sa.Column('category', sa.String(255), nullable=True),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('availability', sa.String(100), nullable=True),
            sa.Column('images', sa.Text, nullable=True),
            sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp(), nullable=True),
            sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp(), nullable=True),
        )
    else:
        # Table exists, check and add missing columns
        existing_columns = [col['name'] for col in inspector.get_columns('products')]
        
        # Add user_id if missing
        if 'user_id' not in existing_columns:
            op.add_column('products', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
        
        # Add category if missing
        if 'category' not in existing_columns:
            op.add_column('products', sa.Column('category', sa.String(255), nullable=True))
        
        # Add created_at if missing (might be crawled_at instead)
        if 'created_at' not in existing_columns and 'crawled_at' not in existing_columns:
            op.add_column('products', sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp(), nullable=True))
    
    # Refresh inspector to get updated table structure
    inspector = inspect(conn)
    
    # Create indexes if they don't exist
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('products')] if 'products' in inspector.get_table_names() else []
    
    # Get current columns to check before creating indexes
    current_columns = [col['name'] for col in inspector.get_columns('products')]
    
    if 'idx_products_url' not in existing_indexes and 'url' in current_columns:
        op.create_index('idx_products_url', 'products', ['url'])
    if 'idx_products_brand' not in existing_indexes and 'brand' in current_columns:
        op.create_index('idx_products_brand', 'products', ['brand'])
    if 'idx_products_price' not in existing_indexes and 'price' in current_columns:
        op.create_index('idx_products_price', 'products', ['price'])
    if 'idx_products_website_id' not in existing_indexes and 'website_id' in current_columns:
        op.create_index('idx_products_website_id', 'products', ['website_id'])
    if 'idx_products_user_id' not in existing_indexes and 'user_id' in current_columns:
        op.create_index('idx_products_user_id', 'products', ['user_id'])


def downgrade() -> None:
    """Drop products table and all indexes"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if table exists
    if 'products' not in inspector.get_table_names():
        return
    
    # Get existing indexes
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('products')]
    
    # Drop indexes if they exist
    if 'idx_products_user_id' in existing_indexes:
        op.drop_index('idx_products_user_id', 'products')
    if 'idx_products_website_id' in existing_indexes:
        op.drop_index('idx_products_website_id', 'products')
    if 'idx_products_price' in existing_indexes:
        op.drop_index('idx_products_price', 'products')
    if 'idx_products_brand' in existing_indexes:
        op.drop_index('idx_products_brand', 'products')
    if 'idx_products_url' in existing_indexes:
        op.drop_index('idx_products_url', 'products')
    
    # Remove columns that were added by this migration if they exist
    existing_columns = [col['name'] for col in inspector.get_columns('products')]
    
    if 'user_id' in existing_columns:
        op.drop_column('products', 'user_id')
    if 'category' in existing_columns:
        op.drop_column('products', 'category')
    if 'created_at' in existing_columns:
        op.drop_column('products', 'created_at')
    
    # Note: We don't drop the table here because it might have been created by eca40d3692b4
    # The table will be dropped by that migration's downgrade
