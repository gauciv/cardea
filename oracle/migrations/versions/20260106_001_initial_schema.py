"""Initial schema - alerts and threat intelligence

Revision ID: 001
Revises: 
Create Date: 2026-01-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Export Alembic revision identifiers (required for migration framework)
__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on', 'upgrade', 'downgrade']


def upgrade() -> None:
    """Create initial database schema for Cardea Oracle."""
    
    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source', sa.String(100), nullable=False, index=True),
        sa.Column('alert_type', sa.String(50), nullable=False, index=True),
        sa.Column('severity', sa.String(20), nullable=False, index=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('threat_score', sa.Float(), nullable=True),
        sa.Column('risk_level', sa.String(20), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(), nullable=True),
        sa.Column('network_context', postgresql.JSONB(), nullable=True),
        sa.Column('correlations', postgresql.JSONB(), nullable=True),
        sa.Column('indicators', postgresql.JSONB(), nullable=True),
    )
    
    # Create composite indexes for common queries
    op.create_index(
        'idx_alerts_timestamp_severity',
        'alerts',
        ['timestamp', 'severity']
    )
    op.create_index(
        'idx_alerts_source_type',
        'alerts',
        ['source', 'alert_type']
    )
    op.create_index(
        'idx_alerts_threat_score',
        'alerts',
        ['threat_score']
    )
    
    # Create threat_intelligence table
    op.create_table(
        'threat_intelligence',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('threat_id', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('threat_type', sa.String(50), nullable=False, index=True),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('indicators', postgresql.JSONB(), nullable=True),
        sa.Column('tactics', postgresql.JSONB(), nullable=True),
        sa.Column('techniques', postgresql.JSONB(), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('alert_id', sa.Integer(), sa.ForeignKey('alerts.id'), nullable=True),
    )


def downgrade() -> None:
    """Remove all tables."""
    op.drop_table('threat_intelligence')
    op.drop_index('idx_alerts_threat_score', table_name='alerts')
    op.drop_index('idx_alerts_source_type', table_name='alerts')
    op.drop_index('idx_alerts_timestamp_severity', table_name='alerts')
    op.drop_table('alerts')
