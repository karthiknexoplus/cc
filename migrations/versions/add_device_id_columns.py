"""add device id columns

Revision ID: add_device_id_columns
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_device_id_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add entry_device_id and exit_device_id columns to vehicle_entry table
    op.add_column('vehicle_entry', sa.Column('entry_device_id', sa.String(3), nullable=True))
    op.add_column('vehicle_entry', sa.Column('exit_device_id', sa.String(3), nullable=True))


def downgrade():
    # Remove the columns if needed to rollback
    op.drop_column('vehicle_entry', 'entry_device_id')
    op.drop_column('vehicle_entry', 'exit_device_id') 