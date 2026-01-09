"""add devices table

Revision ID: 20260109_003
Revises: 20260108_002_users_and_multitenancy
Create Date: 2026-01-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260109_003'
down_revision: Union[str, None] = '20260108_002_users_and_multitenancy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enum Types
    # Check if type exists first to avoid errors on re-run
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'devicestatus') THEN CREATE TYPE devicestatus AS ENUM ('UNCLAIMED', 'ONLINE', 'OFFLINE', 'MAINTENANCE'); END IF; END $$;")
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'devicetype') THEN CREATE TYPE devicetype AS ENUM ('SENTRY_PI', 'SENTRY_LINUX', 'BRIDGE_CLI', 'UNKNOWN'); END IF; END $$;")

    # 2. Create Devices Table
    op.create_table('devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hardware_id', sa.String(length=100), nullable=False),
        sa.Column('friendly_name', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('UNCLAIMED', 'ONLINE', 'OFFLINE', 'MAINTENANCE', name='devicestatus'), nullable=False),
        sa.Column('device_type', sa.Enum('SENTRY_PI', 'SENTRY_LINUX', 'BRIDGE_CLI', 'UNKNOWN', name='devicetype'), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('claim_token', sa.String(length=100), nullable=True),
        sa.Column('api_key', sa.String(length=100), nullable=True),
        sa.Column('public_key', sa.Text(), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_devices_hardware_id'), 'devices', ['hardware_id'], unique=True)
    op.create_index(op.f('ix_devices_id'), 'devices', ['id'], unique=False)
    op.create_index(op.f('ix_devices_user_id'), 'devices', ['user_id'], unique=False)
    op.create_index(op.f('ix_devices_claim_token'), 'devices', ['claim_token'], unique=False)
    
    # 3. Update Alerts Table
    op.add_column('alerts', sa.Column('device_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_alerts_device_id'), 'alerts', ['device_id'], unique=False)
    op.create_foreign_key(None, 'alerts', 'devices', ['device_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    # Drop Alerts column
    op.drop_constraint(None, 'alerts', type_='foreignkey')
    op.drop_index(op.f('ix_alerts_device_id'), table_name='alerts')
    op.drop_column('alerts', 'device_id')
    
    # Drop Devices table
    op.drop_index(op.f('ix_devices_claim_token'), table_name='devices')
    op.drop_index(op.f('ix_devices_user_id'), table_name='devices')
    op.drop_index(op.f('ix_devices_id'), table_name='devices')
    op.drop_index(op.f('ix_devices_hardware_id'), table_name='devices')
    op.drop_table('devices')
    
    # Drop Enums
    op.execute("DROP TYPE devicestatus")
    op.execute("DROP TYPE devicetype")