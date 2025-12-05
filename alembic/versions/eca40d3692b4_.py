"""empty message

Revision ID: eca40d3692b4
Revises: 14582c6d86e7
Create Date: 2025-10-17 09:31:25.923351

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'eca40d3692b4'
down_revision: Union[str, Sequence[str], None] = '14582c6d86e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False),
        sa.Column('website_id', sa.Integer, nullable=False),
        sa.Column('website_name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(1000), nullable=False),
        sa.Column('title', sa.String(500)),
        sa.Column('price', sa.Numeric(20, 2)),
        sa.Column('original_price', sa.Numeric(20, 2)),
        sa.Column('currency', sa.String(10), server_default='VND'),
        sa.Column('sku', sa.String(100)),
        sa.Column('brand', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('availability', sa.String(100)),
        sa.Column('images', sa.Text),
        sa.Column('crawled_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'products' in inspector.get_table_names():
        op.drop_table('products')