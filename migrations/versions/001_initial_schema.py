"""Initial schema - create all tables

Revision ID: 001
Revises:
Create Date: 2025-11-19 22:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_users'),
        sa.UniqueConstraint('email', name='uq_users_email')
    )
    op.create_index('ix_email', 'users', ['email'])

    # Create products table
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('barcode_gtin', sa.String(length=50), nullable=True),
        sa.Column('current_stock', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('critical_stock_level', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('unit', sa.String(length=50), nullable=False, server_default='adet'),
        sa.Column('unit_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('shelf_life_days', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_products_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_products')
    )
    op.create_index('idx_products_user_id', 'products', ['user_id'])
    op.create_index('idx_products_barcode', 'products', ['barcode_gtin'])
    op.create_index('idx_products_low_stock', 'products', ['user_id', 'current_stock'])
    op.create_index('idx_products_sku', 'products', ['user_id', 'sku'], unique=True)

    # Create receipts table
    op.create_table(
        'receipts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('receipt_number', sa.String(length=100), nullable=True),
        sa.Column('store_name', sa.String(length=255), nullable=True),
        sa.Column('receipt_date', sa.Date(), nullable=True),
        sa.Column('total_amount', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=False),
        sa.Column('image_hash', sa.String(length=64), nullable=True),
        sa.Column('ocr_raw_text', sa.Text(), nullable=True),
        sa.Column('ocr_confidence', sa.DECIMAL(precision=5, scale=4), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_receipts_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_receipts'),
        sa.UniqueConstraint('image_hash', name='uq_receipts_image_hash')
    )
    op.create_index('idx_receipts_user_id', 'receipts', ['user_id'])
    op.create_index('idx_receipts_status', 'receipts', ['processing_status'])
    op.create_index('idx_receipts_date', 'receipts', ['receipt_date'])

    # Create receipt_items table
    op.create_table(
        'receipt_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('receipt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name_raw', sa.String(length=500), nullable=True),
        sa.Column('quantity', sa.DECIMAL(precision=10, scale=3), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('unit_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('total_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('confidence_score', sa.DECIMAL(precision=5, scale=4), nullable=True),
        sa.Column('matched_automatically', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['receipt_id'], ['receipts.id'], name='fk_receipt_items_receipt_id_receipts', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_receipt_items_product_id_products', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_receipt_items')
    )
    op.create_index('idx_receipt_items_receipt', 'receipt_items', ['receipt_id'])
    op.create_index('idx_receipt_items_product', 'receipt_items', ['product_id'])

    # Create stock_transactions table
    op.create_table(
        'stock_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_stock_transactions_user_id_users', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_stock_transactions_product_id_products', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_stock_transactions_created_by_users', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_stock_transactions')
    )
    op.create_index('idx_stock_transactions_user', 'stock_transactions', ['user_id'])
    op.create_index('idx_stock_transactions_product', 'stock_transactions', ['product_id'])
    op.create_index('idx_stock_transactions_type', 'stock_transactions', ['transaction_type'])
    op.create_index('idx_stock_transactions_created_at', 'stock_transactions', ['created_at'])

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_sent_email', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('sent_email_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_alerts_user_id_users', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_alerts_product_id_products', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_alerts')
    )
    op.create_index('idx_alerts_user', 'alerts', ['user_id'])
    op.create_index('idx_alerts_user_unread', 'alerts', ['user_id', 'is_read'])
    op.create_index('idx_alerts_type', 'alerts', ['alert_type'])
    op.create_index('idx_alerts_severity', 'alerts', ['severity'])
    op.create_index('idx_alerts_created_at', 'alerts', ['created_at'])

    # Create email_queue table
    op.create_table(
        'email_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('recipient_email', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('body_html', sa.Text(), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_email_queue_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_email_queue')
    )
    op.create_index('idx_email_queue_user', 'email_queue', ['user_id'])
    op.create_index('idx_email_queue_status', 'email_queue', ['status'])
    op.create_index('idx_email_queue_pending', 'email_queue', ['status', 'created_at'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_audit_logs_user_id_users', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_audit_logs')
    )
    op.create_index('idx_audit_logs_user', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('email_queue')
    op.drop_table('alerts')
    op.drop_table('stock_transactions')
    op.drop_table('receipt_items')
    op.drop_table('receipts')
    op.drop_table('products')
    op.drop_table('users')
