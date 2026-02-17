"""Create communications table for WhatsApp Business API integration.

Revision ID: 20260216_002_whatsapp_communications
Revises: 20260216_001_core_ats_data_model
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260216_002_whatsapp_communications'
down_revision = '20260216_001_core_ats_data_model'
branch_labels = None
depends_on = None


def upgrade():
    # Crear tipos ENUM
    sa.Enum('whatsapp', 'email', 'sms', name='communicationchannel').create(op.get_bind())
    sa.Enum('outbound', 'inbound', name='communicationdirection').create(op.get_bind())
    sa.Enum('initial', 'follow_up', 'reminder', 'reply', name='communicationmessagetype').create(op.get_bind())
    sa.Enum('pending', 'sent', 'delivered', 'read', 'failed', 'replied', name='communicationstatus').create(op.get_bind())
    sa.Enum('interested', 'not_interested', 'unknown', 'question', name='intereststatus').create(op.get_bind())
    
    # Crear tabla communications
    op.create_table(
        'communications',
        sa.Column('communication_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('channel', sa.Enum('whatsapp', 'email', 'sms', name='communicationchannel'), nullable=False),
        sa.Column('direction', sa.Enum('outbound', 'inbound', name='communicationdirection'), nullable=False),
        sa.Column('message_type', sa.Enum('initial', 'follow_up', 'reminder', 'reply', name='communicationmessagetype'), nullable=False),
        sa.Column('template_id', sa.String(length=255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recipient_phone', sa.String(length=25), nullable=True),
        sa.Column('recipient_name', sa.String(length=255), nullable=True),
        sa.Column('whatsapp_message_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.Enum('pending', 'sent', 'delivered', 'read', 'failed', 'replied', name='communicationstatus'), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reply_to_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reply_whatsapp_id', sa.String(length=255), nullable=True),
        sa.Column('reply_content', sa.Text(), nullable=True),
        sa.Column('reply_received_at', sa.DateTime(), nullable=True),
        sa.Column('interest_status', sa.Enum('interested', 'not_interested', 'unknown', 'question', name='intereststatus'), nullable=True),
        sa.Column('response_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('communication_id'),
    )
    
    # Crear índices
    op.create_index('idx_communications_application', 'communications', ['application_id'])
    op.create_index('idx_communications_candidate', 'communications', ['candidate_id'])
    op.create_index('idx_communications_status', 'communications', ['status'])
    op.create_index('idx_communications_whatsapp_id', 'communications', ['whatsapp_message_id'])
    op.create_index('idx_communications_created', 'communications', ['created_at'])
    op.create_index('idx_communications_phone', 'communications', ['recipient_phone'])
    
    # Crear foreign keys
    op.create_foreign_key(
        'fk_communications_application',
        'communications', 'hh_applications',
        ['application_id'], ['application_id']
    )
    op.create_foreign_key(
        'fk_communications_candidate',
        'communications', 'hh_candidates',
        ['candidate_id'], ['candidate_id']
    )
    op.create_foreign_key(
        'fk_communications_reply_to',
        'communications', 'communications',
        ['reply_to_id'], ['communication_id']
    )
    op.create_foreign_key(
        'fk_communications_created_by',
        'communications', 'users',
        ['created_by'], ['id']
    )


def downgrade():
    # Eliminar foreign keys
    op.drop_constraint('fk_communications_application', 'communications', type_='foreignkey')
    op.drop_constraint('fk_communications_candidate', 'communications', type_='foreignkey')
    op.drop_constraint('fk_communications_reply_to', 'communications', type_='foreignkey')
    op.drop_constraint('fk_communications_created_by', 'communications', type_='foreignkey')
    
    # Eliminar índices
    op.drop_index('idx_communications_application', table_name='communications')
    op.drop_index('idx_communications_candidate', table_name='communications')
    op.drop_index('idx_communications_status', table_name='communications')
    op.drop_index('idx_communications_whatsapp_id', table_name='communications')
    op.drop_index('idx_communications_created', table_name='communications')
    op.drop_index('idx_communications_phone', table_name='communications')
    
    # Eliminar tabla
    op.drop_table('communications')
    
    # Eliminar tipos ENUM
    sa.Enum('whatsapp', 'email', 'sms', name='communicationchannel').drop(op.get_bind())
    sa.Enum('outbound', 'inbound', name='communicationdirection').drop(op.get_bind())
    sa.Enum('initial', 'follow_up', 'reminder', 'reply', name='communicationmessagetype').drop(op.get_bind())
    sa.Enum('pending', 'sent', 'delivered', 'read', 'failed', 'replied', name='communicationstatus').drop(op.get_bind())
    sa.Enum('interested', 'not_interested', 'unknown', 'question', name='intereststatus').drop(op.get_bind())
