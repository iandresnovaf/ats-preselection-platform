"""
Migración: Estados detallados de candidatos y campos de contacto
Crea nuevos estados extendidos para el pipeline de aplicaciones
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20260216_2055_detailed_application_stages'
down_revision = '20260216_003'
branch_labels = None
depends_on = None


def upgrade():
    # Crear el nuevo tipo enum para etapas detalladas
    op.execute("""
        CREATE TYPE applicationstage_new AS ENUM (
            'sourcing',
            'shortlist',
            'terna',
            'contact_pending',
            'contacted',
            'interested',
            'not_interested',
            'no_response',
            'interview_scheduled',
            'interview_done',
            'offer_sent',
            'offer_accepted',
            'offer_rejected',
            'hired',
            'discarded'
        )
    """)
    
    # Convertir la columna stage a VARCHAR temporalmente para permitir valores antiguos
    op.execute("""
        ALTER TABLE hh_applications 
        ALTER COLUMN stage TYPE VARCHAR(50)
    """)
    
    # Mapear valores antiguos a nuevos
    op.execute("""
        UPDATE hh_applications 
        SET stage = CASE stage
            WHEN 'interview' THEN 'interview_scheduled'
            WHEN 'offer' THEN 'offer_sent'
            WHEN 'rejected' THEN 'discarded'
            ELSE stage
        END
    """)
    
    # Cambiar la columna al nuevo enum
    op.execute("""
        ALTER TABLE hh_applications 
        ALTER COLUMN stage TYPE applicationstage_new 
        USING stage::applicationstage_new
    """)
    
    # Renombrar tipos
    op.execute("DROP TYPE IF EXISTS applicationstage")
    op.execute("ALTER TYPE applicationstage_new RENAME TO applicationstage")
    
    # Agregar campo para razón de descarte
    op.add_column('hh_applications', 
        sa.Column('discard_reason', sa.Text(), nullable=True)
    )
    
    # Agregar campo para fecha de contacto inicial
    op.add_column('hh_applications',
        sa.Column('initial_contact_date', sa.DateTime(), nullable=True)
    )
    
    # Agregar campo para fecha de respuesta
    op.add_column('hh_applications',
        sa.Column('candidate_response_date', sa.DateTime(), nullable=True)
    )
    
    # Crear índices para los nuevos campos
    op.create_index('idx_hh_applications_discard_reason', 'hh_applications', ['discard_reason'])
    op.create_index('idx_hh_applications_contact_date', 'hh_applications', ['initial_contact_date'])


def downgrade():
    # Eliminar índices
    op.drop_index('idx_hh_applications_contact_date', table_name='hh_applications')
    op.drop_index('idx_hh_applications_discard_reason', table_name='hh_applications')
    
    # Eliminar columnas
    op.drop_column('hh_applications', 'candidate_response_date')
    op.drop_column('hh_applications', 'initial_contact_date')
    op.drop_column('hh_applications', 'discard_reason')
    
    # Crear tipo enum antiguo
    op.execute("""
        CREATE TYPE applicationstage_old AS ENUM (
            'sourcing',
            'shortlist',
            'terna',
            'interview',
            'offer',
            'hired',
            'rejected'
        )
    """)
    
    # Convertir valores nuevos a antiguos
    op.execute("""
        ALTER TABLE hh_applications 
        ALTER COLUMN stage TYPE VARCHAR(50)
    """)
    
    op.execute("""
        UPDATE hh_applications 
        SET stage = CASE stage
            WHEN 'interview_scheduled' THEN 'interview'
            WHEN 'interview_done' THEN 'interview'
            WHEN 'offer_sent' THEN 'offer'
            WHEN 'offer_accepted' THEN 'offer'
            WHEN 'offer_rejected' THEN 'offer'
            WHEN 'discarded' THEN 'rejected'
            WHEN 'contact_pending' THEN 'sourcing'
            WHEN 'contacted' THEN 'shortlist'
            WHEN 'interested' THEN 'shortlist'
            WHEN 'not_interested' THEN 'rejected'
            WHEN 'no_response' THEN 'rejected'
            ELSE stage
        END
    """)
    
    op.execute("""
        ALTER TABLE hh_applications 
        ALTER COLUMN stage TYPE applicationstage_old 
        USING stage::applicationstage_old
    """)
    
    op.execute("DROP TYPE applicationstage")
    op.execute("ALTER TYPE applicationstage_old RENAME TO applicationstage")
