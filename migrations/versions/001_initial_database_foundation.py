"""001_initial_database_foundation

Revision ID: 001_initial_foundation
Revises: 
Create Date: 2026-11-13 17:46:00.000000+00:00

Initial database foundation for MIORA Postpartum Depression Screening Platform:
- mothers: Demographics, medical record numbers, high risk indicator
- screenings: EPDS/instrument scores, multimodal statuses and outputs, Q10 alerts
- clinical_reviews: Clinician verifications, risk overrides, qualitative impressions
- care_plans: Prioritized interventions, referral routes, follow-up scheduling
- audit_logs: Immutable compliance logging for clinical actions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_foundation'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. mothers table
    op.create_table(
        'mothers',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('medical_record_number', sa.String(length=64), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('delivery_date', sa.Date(), nullable=True),
        sa.Column('parity', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('contact_phone', sa.String(length=32), nullable=True),
        sa.Column('contact_email', sa.String(length=128), nullable=True),
        sa.Column('emergency_contact_name', sa.String(length=100), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(length=32), nullable=True),
        sa.Column('primary_language', sa.String(length=32), nullable=True, server_default='English'),
        sa.Column('high_risk_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_mothers_medical_record_number'), 'mothers', ['medical_record_number'], unique=True)
    op.create_index(op.f('ix_mothers_contact_phone'), 'mothers', ['contact_phone'], unique=False)
    op.create_index(op.f('ix_mothers_high_risk_flag'), 'mothers', ['high_risk_flag'], unique=False)
    op.create_index(op.f('ix_mothers_is_active'), 'mothers', ['is_active'], unique=False)

    # 2. screenings table
    op.create_table(
        'screenings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('mother_id', sa.Uuid(), nullable=False),
        sa.Column('screening_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('instrument', sa.String(length=64), nullable=False, server_default='EPDS'),
        sa.Column('total_score', sa.Integer(), nullable=False),
        sa.Column('risk_classification', sa.String(length=32), nullable=False),
        sa.Column('q10_safety_alert', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('submitted_answers', sa.JSON(), nullable=False),
        sa.Column('item_scores', sa.JSON(), nullable=False),
        sa.Column('modality_status', sa.JSON(), nullable=False),
        sa.Column('model_metadata', sa.JSON(), nullable=False),
        sa.Column('multimodal_scores', sa.JSON(), nullable=False),
        sa.Column('screening_status', sa.String(length=32), nullable=False, server_default='COMPLETED'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['mother_id'], ['mothers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_screenings_mother_id'), 'screenings', ['mother_id'], unique=False)
    op.create_index(op.f('ix_screenings_screening_date'), 'screenings', ['screening_date'], unique=False)
    op.create_index(op.f('ix_screenings_risk_classification'), 'screenings', ['risk_classification'], unique=False)
    op.create_index(op.f('ix_screenings_q10_safety_alert'), 'screenings', ['q10_safety_alert'], unique=False)
    op.create_index(op.f('ix_screenings_screening_status'), 'screenings', ['screening_status'], unique=False)
    op.create_index('ix_screenings_mother_date', 'screenings', ['mother_id', 'screening_date'], unique=False)
    op.create_index('ix_screenings_risk_alert', 'screenings', ['risk_classification', 'q10_safety_alert'], unique=False)

    # 3. clinical_reviews table
    op.create_table(
        'clinical_reviews',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('mother_id', sa.Uuid(), nullable=False),
        sa.Column('screening_id', sa.Uuid(), nullable=True),
        sa.Column('clinician_id', sa.String(length=64), nullable=False),
        sa.Column('clinician_name', sa.String(length=128), nullable=False),
        sa.Column('review_status', sa.String(length=32), nullable=False, server_default='PENDING'),
        sa.Column('final_risk_classification', sa.String(length=32), nullable=True),
        sa.Column('clinical_notes', sa.Text(), nullable=True),
        sa.Column('required_immediate_escalation', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['mother_id'], ['mothers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['screening_id'], ['screenings.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_clinical_reviews_mother_id'), 'clinical_reviews', ['mother_id'], unique=False)
    op.create_index(op.f('ix_clinical_reviews_screening_id'), 'clinical_reviews', ['screening_id'], unique=False)
    op.create_index(op.f('ix_clinical_reviews_clinician_id'), 'clinical_reviews', ['clinician_id'], unique=False)
    op.create_index(op.f('ix_clinical_reviews_review_status'), 'clinical_reviews', ['review_status'], unique=False)
    op.create_index(op.f('ix_clinical_reviews_required_immediate_escalation'), 'clinical_reviews', ['required_immediate_escalation'], unique=False)
    op.create_index('ix_clinical_reviews_clinician_date', 'clinical_reviews', ['clinician_id', 'reviewed_at'], unique=False)

    # 4. care_plans table
    op.create_table(
        'care_plans',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('mother_id', sa.Uuid(), nullable=False),
        sa.Column('screening_id', sa.Uuid(), nullable=True),
        sa.Column('priority', sa.String(length=32), nullable=False, server_default='ROUTINE'),
        sa.Column('intervention_type', sa.String(length=64), nullable=False),
        sa.Column('referral_destination', sa.String(length=128), nullable=True),
        sa.Column('scheduled_followup_date', sa.Date(), nullable=True),
        sa.Column('assigned_clinician_id', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['mother_id'], ['mothers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['screening_id'], ['screenings.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_care_plans_mother_id'), 'care_plans', ['mother_id'], unique=False)
    op.create_index(op.f('ix_care_plans_screening_id'), 'care_plans', ['screening_id'], unique=False)
    op.create_index(op.f('ix_care_plans_priority'), 'care_plans', ['priority'], unique=False)
    op.create_index(op.f('ix_care_plans_status'), 'care_plans', ['status'], unique=False)
    op.create_index(op.f('ix_care_plans_assigned_clinician_id'), 'care_plans', ['assigned_clinician_id'], unique=False)
    op.create_index(op.f('ix_care_plans_scheduled_followup_date'), 'care_plans', ['scheduled_followup_date'], unique=False)
    op.create_index('ix_care_plans_priority_status', 'care_plans', ['priority', 'status'], unique=False)
    op.create_index('ix_care_plans_followup_status', 'care_plans', ['scheduled_followup_date', 'status'], unique=False)

    # 5. audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=False),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('actor_role', sa.String(length=32), nullable=False, server_default='CLINICIAN'),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('client_ip', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_type'), 'audit_logs', ['resource_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_id'), 'audit_logs', ['resource_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_actor_id'), 'audit_logs', ['actor_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_actor_action', 'audit_logs', ['actor_id', 'action'], unique=False)
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('care_plans')
    op.drop_table('clinical_reviews')
    op.drop_table('screenings')
    op.drop_table('mothers')

