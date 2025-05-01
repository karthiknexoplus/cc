"""add device id columns

Revision ID: add_device_id_columns
Revises: cf7f29b6623d
Create Date: 2024-04-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_device_id_columns'
down_revision = 'cf7f29b6623d'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns
    op.add_column('vehicle_entry', sa.Column('entry_device_id', sa.String(3), nullable=True))
    op.add_column('vehicle_entry', sa.Column('exit_device_id', sa.String(3), nullable=True))
    
    # Copy data from device_id to entry_device_id
    op.execute("UPDATE vehicle_entry SET entry_device_id = device_id")
    
    # Drop the old device_id column
    op.drop_column('vehicle_entry', 'device_id')

def downgrade():
    # Add back the device_id column
    op.add_column('vehicle_entry', sa.Column('device_id', sa.String(3), nullable=True))
    
    # Copy data from entry_device_id to device_id
    op.execute("UPDATE vehicle_entry SET device_id = entry_device_id")
    
    # Drop the new columns
    op.drop_column('vehicle_entry', 'exit_device_id')
    op.drop_column('vehicle_entry', 'entry_device_id') 