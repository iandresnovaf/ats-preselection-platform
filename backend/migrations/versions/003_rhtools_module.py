"""RHTools module migration

Revision ID: 003_rhtools_module
Revises: 20260211_1415_002_core_ats
Create Date: 2026-02-12 00:44:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '003_rhtools_module'
down_revision = '002_core_ats'
branch_labels = None
depends_on = None


def upgrade():
    # ### Crear tabla accounts (multi-tenancy) ###
    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('settings_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_accounts_slug', 'accounts', ['slug'], unique=True)
    
    # Insertar cuenta por defecto
    default_account_id = '00000000-0000-0000-0000-000000000001'
    op.execute(f"""
        INSERT INTO accounts (id, name, slug, status, created_at, updated_at)
        VALUES ('{default_account_id}', 'Default Account', 'default', 'active', NOW(), NOW())
    """)
    
    # ### Campos nuevos en tablas existentes ###
    
    # job_openings - campos adicionales para RHTools
    op.add_column('job_openings', sa.Column('confidentiality_level', sa.String(20), nullable=True, server_default='public'))
    op.add_column('job_openings', sa.Column('fee_model', sa.String(20), nullable=True))
    op.add_column('job_openings', sa.Column('fee_amount', sa.Numeric(10, 2), nullable=True))
    op.add_column('job_openings', sa.Column('fee_currency', sa.String(3), nullable=True))
    op.add_column('job_openings', sa.Column('intake_notes', sa.Text(), nullable=True))
    op.add_column('job_openings', sa.Column('must_haves_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('job_openings', sa.Column('nice_to_haves_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('job_openings', sa.Column('compensation_range_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('job_openings', sa.Column('offlimits_days_override', sa.Integer(), nullable=True))
    op.add_column('job_openings', sa.Column('senior_consultant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('job_openings', sa.Column('pipeline_template_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    op.create_foreign_key('fk_job_openings_senior_consultant', 'job_openings', 'users', ['senior_consultant_id'], ['id'])
    
    # candidates - campos adicionales para RHTools
    op.add_column('candidates', sa.Column('primary_email', sa.String(255), nullable=True))
    op.add_column('candidates', sa.Column('primary_phone', sa.String(50), nullable=True))
    op.add_column('candidates', sa.Column('phone_country', sa.String(5), nullable=True))
    op.add_column('candidates', sa.Column('location_text', sa.String(255), nullable=True))
    op.add_column('candidates', sa.Column('country', sa.String(100), nullable=True))
    op.add_column('candidates', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('candidates', sa.Column('linkedin_url', sa.String(500), nullable=True))
    op.add_column('candidates', sa.Column('portfolio_url', sa.String(500), nullable=True))
    op.add_column('candidates', sa.Column('headline', sa.String(255), nullable=True))
    op.add_column('candidates', sa.Column('summary_text', sa.Text(), nullable=True))
    
    # Índices para campos nuevos
    op.create_index('ix_candidates_primary_email', 'candidates', ['primary_email'])
    op.create_index('ix_candidates_primary_phone', 'candidates', ['primary_phone'])
    
    # ### Nuevas tablas RHTools ###
    
    # clients
    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('legal_name', sa.String(255), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_clients_account_id', 'clients', ['account_id'])
    op.create_index('ix_clients_status', 'clients', ['status'])
    
    # client_contacts
    op.create_table(
        'client_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('whatsapp', sa.String(50), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_client_contacts_account_id', 'client_contacts', ['account_id'])
    op.create_index('ix_client_contacts_client_id', 'client_contacts', ['client_id'])
    
    # pipeline_templates
    op.create_table(
        'pipeline_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_pipeline_templates_account_id', 'pipeline_templates', ['account_id'])
    op.create_index('ix_pipeline_templates_is_default', 'pipeline_templates', ['is_default'])
    
    # pipeline_stages
    op.create_table(
        'pipeline_stages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pipeline_template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipeline_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('stage_key', sa.String(100), nullable=False),  # slug estable
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('stage_type', sa.String(50), nullable=False, server_default='custom'),  # sourcing/screening/interview/offer/hired/rejected/custom
        sa.Column('is_terminal', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_visible_to_client', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('requires_feedback', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sla_days', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_pipeline_stages_account_id', 'pipeline_stages', ['account_id'])
    op.create_index('ix_pipeline_stages_pipeline_template_id', 'pipeline_stages', ['pipeline_template_id'])
    op.create_index('ix_pipeline_stages_stage_key', 'pipeline_stages', ['stage_key'])
    op.create_index('ix_pipeline_stages_order_index', 'pipeline_stages', ['order_index'])
    
    # stage_required_fields
    op.create_table(
        'stage_required_fields',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipeline_stages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('field_key', sa.String(100), nullable=False),
        sa.Column('is_blocking', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_stage_required_fields_stage_id', 'stage_required_fields', ['stage_id'])
    
    # candidate_offlimits
    op.create_table(
        'candidate_offlimits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reason', sa.String(50), nullable=False),  # placed, other
        sa.Column('offlimits_from', sa.Date(), nullable=False),
        sa.Column('offlimits_until', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),  # active, expired, removed_manual
        sa.Column('placed_search_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_openings.id'), nullable=True),
        sa.Column('placed_submission_id', postgresql.UUID(as_uuid=True), nullable=True),  # FK a submissions cuando exista
        sa.Column('set_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('unset_by_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('unset_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_candidate_offlimits_account_id', 'candidate_offlimits', ['account_id'])
    op.create_index('ix_candidate_offlimits_candidate_id', 'candidate_offlimits', ['candidate_id'])
    op.create_index('ix_candidate_offlimits_status', 'candidate_offlimits', ['status'])
    
    # submissions
    op.create_table(
        'submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('search_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_openings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_consultant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('current_stage_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipeline_stages.id'), nullable=True),
        sa.Column('stage_changed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),  # active, rejected, placed, withdrawn
        sa.Column('overall_score', sa.Integer(), nullable=True),
        sa.Column('score_breakdown_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('salary_expectation_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('availability_text', sa.Text(), nullable=True),
        sa.Column('notes_internal', sa.Text(), nullable=True),
        sa.Column('notes_client_safe', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_submissions_account_id', 'submissions', ['account_id'])
    op.create_index('ix_submissions_candidate_id', 'submissions', ['candidate_id'])
    op.create_index('ix_submissions_search_id', 'submissions', ['search_id'])
    op.create_index('ix_submissions_current_stage_id', 'submissions', ['current_stage_id'])
    op.create_index('ix_submissions_status', 'submissions', ['status'])
    
    # submission_stage_history
    op.create_table(
        'submission_stage_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('submissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_stage_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipeline_stages.id'), nullable=True),
        sa.Column('to_stage_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipeline_stages.id'), nullable=False),
        sa.Column('changed_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
    )
    op.create_index('ix_submission_stage_history_submission_id', 'submission_stage_history', ['submission_id'])
    op.create_index('ix_submission_stage_history_changed_at', 'submission_stage_history', ['changed_at'])
    
    # documents (unificado para CVs, job descriptions, etc.)
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('owner_type', sa.String(50), nullable=False),  # candidate, search, submission
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doc_type', sa.String(50), nullable=False),  # cv, job_description, brief, nda, other
        sa.Column('visibility', sa.String(20), nullable=False, server_default='internal'),  # internal, client_safe
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('storage_provider', sa.String(50), nullable=False, server_default='s3'),
        sa.Column('storage_path', sa.String(1000), nullable=False),
        sa.Column('sha256_hash', sa.String(64), nullable=True),
        sa.Column('uploaded_by_type', sa.String(50), nullable=True),  # user, candidate_portal
        sa.Column('uploaded_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_documents_account_id', 'documents', ['account_id'])
    op.create_index('ix_documents_owner_type_owner_id', 'documents', ['owner_type', 'owner_id'])
    op.create_index('ix_documents_doc_type', 'documents', ['doc_type'])
    op.create_index('ix_documents_visibility', 'documents', ['visibility'])
    
    # document_text_extractions
    op.create_table(
        'document_text_extractions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('language', sa.String(10), nullable=True),
        sa.Column('extraction_method', sa.String(50), nullable=True),  # pypdf, textract, ocr
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_document_text_extractions_document_id', 'document_text_extractions', ['document_id'])
    
    # resume_parses
    op.create_table(
        'resume_parses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('parsed_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('model_id', sa.String(100), nullable=True),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_resume_parses_document_id', 'resume_parses', ['document_id'])
    op.create_index('ix_resume_parses_candidate_id', 'resume_parses', ['candidate_id'])
    
    # candidate_profile_versions
    op.create_table(
        'candidate_profile_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),  # cv_parse, recruiter_edit
        sa.Column('profile_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_by_type', sa.String(50), nullable=True),  # user, system
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_candidate_profile_versions_candidate_id', 'candidate_profile_versions', ['candidate_id'])
    
    # message_templates
    op.create_table(
        'message_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),  # email, whatsapp
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subject_template', sa.String(500), nullable=True),
        sa.Column('body_template', sa.Text(), nullable=False),
        sa.Column('variables_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_message_templates_account_id', 'message_templates', ['account_id'])
    op.create_index('ix_message_templates_channel', 'message_templates', ['channel'])
    
    # stage_message_rules
    op.create_table(
        'stage_message_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pipeline_template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipeline_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipeline_stages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('trigger', sa.String(50), nullable=False),  # on_enter, on_exit
        sa.Column('channel', sa.String(20), nullable=False),  # email, whatsapp
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('message_templates.id'), nullable=False),
        sa.Column('sender_mode', sa.String(50), nullable=True),  # assigned_consultant, specific_user, candidate
        sa.Column('sender_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('recipient_mode', sa.String(50), nullable=True),
        sa.Column('condition_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_stage_message_rules_pipeline_template_id', 'stage_message_rules', ['pipeline_template_id'])
    op.create_index('ix_stage_message_rules_stage_id', 'stage_message_rules', ['stage_id'])
    
    # messages
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=True),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('submissions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('search_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_openings.id', ondelete='CASCADE'), nullable=True),
        sa.Column('channel', sa.String(20), nullable=False),  # email, whatsapp
        sa.Column('direction', sa.String(20), nullable=False),  # outbound, inbound
        sa.Column('to_address', sa.String(500), nullable=True),
        sa.Column('from_address', sa.String(500), nullable=True),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),  # sendgrid, aws_ses, twilio
        sa.Column('provider_message_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),  # pending, sent, delivered, failed
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_messages_account_id', 'messages', ['account_id'])
    op.create_index('ix_messages_candidate_id', 'messages', ['candidate_id'])
    op.create_index('ix_messages_submission_id', 'messages', ['submission_id'])
    op.create_index('ix_messages_status', 'messages', ['status'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])
    
    # tasks
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('related_type', sa.String(50), nullable=True),  # candidate, submission, search, client
        sa.Column('related_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),  # low, medium, high, urgent
        sa.Column('due_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),  # open, in_progress, completed, cancelled
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_tasks_account_id', 'tasks', ['account_id'])
    op.create_index('ix_tasks_owner_user_id', 'tasks', ['owner_user_id'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])
    op.create_index('ix_tasks_due_at', 'tasks', ['due_at'])
    
    # scheduled_jobs
    op.create_table(
        'scheduled_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_type', sa.String(100), nullable=False),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('run_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),  # pending, running, completed, failed, cancelled
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_scheduled_jobs_account_id', 'scheduled_jobs', ['account_id'])
    op.create_index('ix_scheduled_jobs_status', 'scheduled_jobs', ['status'])
    op.create_index('ix_scheduled_jobs_run_at', 'scheduled_jobs', ['run_at'])


def downgrade():
    # Eliminar tablas en orden inverso (respetando foreign keys)
    op.drop_table('scheduled_jobs')
    op.drop_table('tasks')
    op.drop_table('messages')
    op.drop_table('stage_message_rules')
    op.drop_table('message_templates')
    op.drop_table('candidate_profile_versions')
    op.drop_table('resume_parses')
    op.drop_table('document_text_extractions')
    op.drop_table('documents')
    op.drop_table('submission_stage_history')
    op.drop_table('submissions')
    op.drop_table('candidate_offlimits')
    op.drop_table('stage_required_fields')
    op.drop_table('pipeline_stages')
    op.drop_table('pipeline_templates')
    op.drop_table('client_contacts')
    op.drop_table('clients')
    
    # Eliminar índices de candidates
    op.drop_index('ix_candidates_primary_phone', table_name='candidates')
    op.drop_index('ix_candidates_primary_email', table_name='candidates')
    
    # Eliminar columnas de candidates
    op.drop_column('candidates', 'summary_text')
    op.drop_column('candidates', 'headline')
    op.drop_column('candidates', 'portfolio_url')
    op.drop_column('candidates', 'linkedin_url')
    op.drop_column('candidates', 'city')
    op.drop_column('candidates', 'country')
    op.drop_column('candidates', 'location_text')
    op.drop_column('candidates', 'phone_country')
    op.drop_column('candidates', 'primary_phone')
    op.drop_column('candidates', 'primary_email')
    
    # Eliminar columnas de job_openings
    op.drop_constraint('fk_job_openings_senior_consultant', 'job_openings', type_='foreignkey')
    op.drop_column('job_openings', 'pipeline_template_id')
    op.drop_column('job_openings', 'senior_consultant_id')
    op.drop_column('job_openings', 'offlimits_days_override')
    op.drop_column('job_openings', 'compensation_range_json')
    op.drop_column('job_openings', 'nice_to_haves_json')
    op.drop_column('job_openings', 'must_haves_json')
    op.drop_column('job_openings', 'intake_notes')
    op.drop_column('job_openings', 'fee_currency')
    op.drop_column('job_openings', 'fee_amount')
    op.drop_column('job_openings', 'fee_model')
    op.drop_column('job_openings', 'confidentiality_level')
    
    # Eliminar tabla accounts al final
    op.drop_table('accounts')
