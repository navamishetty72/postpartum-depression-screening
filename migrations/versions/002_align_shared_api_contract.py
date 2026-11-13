"""002_align_shared_api_contract

Revision ID: 002_align_contract
Revises: 001_initial_foundation
Create Date: 2026-11-13 17:55:00.000000+00:00

Align models with the team's shared API contract:
- mothers: align fields to (id, name, age, phone, email, delivery_date, pregnancy_type, medical_history, notes)
- screenings: add fusion_status column and composite status index
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_align_contract'
down_revision: Union[str, None] = '001_initial_foundation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update mothers table columns to match contract
    with op.batch_alter_table('mothers') as batch_op:
        # Drop columns not in shared contract
        batch_op.drop_index('ix_mothers_medical_record_number')
        batch_op.drop_column('medical_record_number')
        batch_op.drop_column('first_name')
        batch_op.drop_column('last_name')
        batch_op.drop_column('date_of_birth')
        batch_op.drop_column('parity')
        batch_op.drop_column('emergency_contact_name')
        batch_op.drop_column('emergency_contact_phone')
        batch_op.drop_column('primary_language')
        batch_op.drop_column('high_risk_flag')
        batch_op.drop_column('is_active')
        batch_op.drop_index('ix_mothers_contact_phone')
        batch_op.drop_column('contact_phone')
        batch_op.drop_column('contact_email')

        # Add contract fields
        batch_op.add_column(sa.Column('name', sa.String(length=200), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('age', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('phone', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('email', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('pregnancy_type', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('medical_history', sa.Text(), nullable=True))
        batch_op.create_index('ix_mothers_name', ['name'])
        batch_op.create_index('ix_mothers_phone', ['phone'])
        batch_op.create_index('ix_mothers_email', ['email'])

    # 2. Add fusion_status to screenings
    with op.batch_alter_table('screenings') as batch_op:
        batch_op.add_column(sa.Column('fusion_status', sa.String(length=32), nullable=False, server_default='not_available'))
        batch_op.create_index('ix_screenings_statuses', ['screening_status', 'fusion_status'])


def downgrade() -> None:
    with op.batch_alter_table('screenings') as batch_op:
        batch_op.drop_index('ix_screenings_statuses')
        batch_op.drop_column('fusion_status')

    with op.batch_alter_table('mothers') as batch_op:
        batch_op.drop_index('ix_mothers_email')
        batch_op.drop_index('ix_mothers_phone')
        batch_op.drop_index('ix_mothers_name')
        batch_op.drop_column('medical_history')
        batch_op.drop_column('pregnancy_type')
        batch_op.drop_column('email')
        batch_op.drop_column('phone')
        batch_op.drop_column('age')
        batch_op.drop_column('name')
        batch_op.add_column(sa.Column('medical_record_number', sa.String(length=64), nullable=False))
        batch_op.add_column(sa.Column('first_name', sa.String(length=100), nullable=False))
        batch_op.add_column(sa.Column('last_name', sa.String(length=100), nullable=False))
        batch_op.create_index('ix_mothers_medical_record_number', ['medical_record_number'], unique=True)

