"""
CV Processing Tables Migration
Revision ID: 20260217_1511_cv_processing_tables
Revises: 20260216_002_whatsapp_communications
Create Date: 2026-02-17 15:11:00

Esta migración agrega las tablas necesarias para el procesamiento completo de CVs:
- hh_cv_processing: Almacena texto raw, JSON estructurado y metadatos de extracción
- hh_cv_versions: Histórico de versiones de CV
- hh_cv_processing_logs: Logs detallados del pipeline de procesamiento

Incluye:
- ENUMs para métodos de extracción y estados
- Índices optimizados para performance
- Constraints de integridad referencial
- Triggers para updated_at
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260217_1511_cv_processing_tables'
down_revision = '20260216_2055_detailed_application_stages'
branch_labels = None
depends_on = None


def upgrade():
    # =============================================================================
    # ENUMS
    # =============================================================================
    
    # ExtractionMethod enum
    extractionmethod = postgresql.ENUM(
        'pdf_text', 'ocr', 'ai_extraction', 'hybrid', 'manual',
        name='extractionmethod'
    )
    extractionmethod.create(op.get_bind())
    
    # ProcessingStatus enum
    processingstatus = postgresql.ENUM(
        'pending', 'processing', 'completed', 'failed', 'partial',
        name='processingstatus'
    )
    processingstatus.create(op.get_bind())
    
    # CVVersionStatus enum
    cvversionstatus = postgresql.ENUM(
        'active', 'archived', 'superceded',
        name='cvversionstatus'
    )
    cvversionstatus.create(op.get_bind())
    
    # =============================================================================
    # TABLA 1: HH_CV_PROCESSING
    # =============================================================================
    op.create_table(
        'hh_cv_processing',
        sa.Column('processing_id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=True),
        sa.Column(
            'processing_status',
            sa.Enum('pending', 'processing', 'completed', 'failed', 'partial', name='processingstatus'),
            nullable=False,
            server_default='pending'
        ),
        sa.Column(
            'extraction_method',
            sa.Enum('pdf_text', 'ocr', 'ai_extraction', 'hybrid', 'manual', name='extractionmethod'),
            nullable=True
        ),
        # Contenido extraído
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('extracted_json', postgresql.JSONB(), nullable=True),
        # Metadatos de extracción
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('extraction_duration_ms', sa.Integer(), nullable=True),
        sa.Column('pages_processed', sa.Integer(), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        # Campos específicos extraídos (denormalizados para búsquedas)
        sa.Column('extracted_name', sa.Text(), nullable=True),
        sa.Column('extracted_email', sa.Text(), nullable=True),
        sa.Column('extracted_phone', sa.Text(), nullable=True),
        sa.Column('extracted_title', sa.Text(), nullable=True),
        sa.Column('extracted_location', sa.Text(), nullable=True),
        sa.Column('years_experience', sa.Integer(), nullable=True),
        # Metadata
        sa.Column('processed_by', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        # Constraints
        sa.PrimaryKeyConstraint('processing_id'),
        sa.ForeignKeyConstraint(['candidate_id'], ['hh_candidates.candidate_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['hh_documents.document_id'], ondelete='SET NULL'),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 100', name='chk_cv_processing_confidence')
    )
    
    # Índices para hh_cv_processing
    op.create_index('idx_hh_cv_processing_candidate', 'hh_cv_processing', ['candidate_id'])
    op.create_index('idx_hh_cv_processing_document', 'hh_cv_processing', ['document_id'])
    op.create_index('idx_hh_cv_processing_status', 'hh_cv_processing', ['processing_status'])
    op.create_index('idx_hh_cv_processing_method', 'hh_cv_processing', ['extraction_method'])
    op.create_index('idx_hh_cv_processing_created', 'hh_cv_processing', ['created_at'])
    op.create_index('idx_hh_cv_processing_score', 'hh_cv_processing', ['confidence_score'])
    op.create_index('idx_hh_cv_processing_processed_at', 'hh_cv_processing', ['processed_at'])
    # Índice parcial para búsquedas por email extraído
    op.create_index(
        'idx_hh_cv_processing_extracted_email',
        'hh_cv_processing',
        ['extracted_email'],
        postgresql_where=sa.text('extracted_email IS NOT NULL')
    )
    # Índice GIN para búsquedas JSONB
    op.create_index(
        'idx_hh_cv_processing_extracted_json_gin',
        'hh_cv_processing',
        ['extracted_json'],
        postgresql_using='gin'
    )
    
    # =============================================================================
    # TABLA 2: HH_CV_VERSIONS
    # =============================================================================
    op.create_table(
        'hh_cv_versions',
        sa.Column('version_id', sa.UUID(), nullable=False),
        sa.Column('processing_id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column(
            'version_status',
            sa.Enum('active', 'archived', 'superceded', name='cvversionstatus'),
            nullable=False,
            server_default='active'
        ),
        sa.Column('previous_version_id', sa.UUID(), nullable=True),
        # Contenido de la versión
        sa.Column('version_raw_text', sa.Text(), nullable=True),
        sa.Column('version_extracted_json', postgresql.JSONB(), nullable=True),
        sa.Column('changes_summary', sa.Text(), nullable=True),
        sa.Column('changes_json', postgresql.JSONB(), nullable=True),
        # Metadata
        sa.Column('created_by', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.Column('archive_reason', sa.Text(), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint('version_id'),
        sa.ForeignKeyConstraint(['processing_id'], ['hh_cv_processing.processing_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['hh_candidates.candidate_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['previous_version_id'], ['hh_cv_versions.version_id'], ondelete='SET NULL')
    )
    
    # Índices para hh_cv_versions
    op.create_index('idx_hh_cv_versions_processing', 'hh_cv_versions', ['processing_id'])
    op.create_index('idx_hh_cv_versions_candidate', 'hh_cv_versions', ['candidate_id'])
    op.create_index('idx_hh_cv_versions_status', 'hh_cv_versions', ['version_status'])
    op.create_index('idx_hh_cv_versions_created', 'hh_cv_versions', ['created_at'])
    # Índice único compuesto para número de versión por candidato
    op.create_index(
        'idx_hh_cv_versions_number',
        'hh_cv_versions',
        ['candidate_id', 'version_number']
    )
    # Índice único parcial para solo una versión activa por candidato
    op.create_index(
        'idx_hh_cv_versions_active_unique',
        'hh_cv_versions',
        ['candidate_id', 'version_number'],
        unique=True,
        postgresql_where=sa.text("version_status = 'active'")
    )
    
    # =============================================================================
    # TABLA 3: HH_CV_PROCESSING_LOGS
    # =============================================================================
    op.create_table(
        'hh_cv_processing_logs',
        sa.Column('log_id', sa.UUID(), nullable=False),
        sa.Column('processing_id', sa.UUID(), nullable=False),
        sa.Column('log_level', sa.Text(), nullable=False),
        sa.Column('processing_stage', sa.Text(), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('memory_mb', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        # Constraints
        sa.PrimaryKeyConstraint('log_id'),
        sa.ForeignKeyConstraint(['processing_id'], ['hh_cv_processing.processing_id'], ondelete='CASCADE'),
        sa.CheckConstraint("log_level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR')", name='chk_cv_logs_level')
    )
    
    # Índices para hh_cv_processing_logs
    op.create_index('idx_hh_cv_logs_processing', 'hh_cv_processing_logs', ['processing_id'])
    op.create_index('idx_hh_cv_logs_level', 'hh_cv_processing_logs', ['log_level'])
    op.create_index('idx_hh_cv_logs_stage', 'hh_cv_processing_logs', ['processing_stage'])
    op.create_index('idx_hh_cv_logs_created', 'hh_cv_processing_logs', ['created_at'])
    op.create_index(
        'idx_hh_cv_logs_step',
        'hh_cv_processing_logs',
        ['processing_id', 'step_order']
    )
    
    # =============================================================================
    # TRIGGERS PARA ACTUALIZAR updated_at
    # =============================================================================
    
    # Trigger para hh_cv_processing
    op.execute("""
        CREATE TRIGGER trg_hh_cv_processing_updated_at
            BEFORE UPDATE ON hh_cv_processing
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # =============================================================================
    # VISTAS ÚTILES
    # =============================================================================
    
    # Vista de candidatos con último CV procesado
    op.execute("""
        CREATE OR REPLACE VIEW v_candidates_cv_summary AS
        SELECT 
            c.candidate_id,
            c.full_name,
            c.email as candidate_email,
            c.phone as candidate_phone,
            cvp.processing_id as last_cv_processing_id,
            cvp.processed_at as last_cv_processed_at,
            cvp.extraction_method as last_cv_method,
            cvp.confidence_score as last_cv_confidence,
            cvp.years_experience,
            cvp.extracted_title,
            cvp.extracted_location,
            cvv.version_id as active_version_id,
            cvv.version_number as active_version_number
        FROM hh_candidates c
        LEFT JOIN LATERAL (
            SELECT * FROM hh_cv_processing
            WHERE candidate_id = c.candidate_id
            AND processing_status = 'completed'
            ORDER BY processed_at DESC
            LIMIT 1
        ) cvp ON true
        LEFT JOIN hh_cv_versions cvv ON cvv.processing_id = cvp.processing_id 
            AND cvv.version_status = 'active';
    """)
    
    # Vista de procesamiento de CVs con conteo de logs
    op.execute("""
        CREATE OR REPLACE VIEW v_cv_processing_summary AS
        SELECT 
            cvp.processing_id,
            cvp.candidate_id,
            cvp.processing_status,
            cvp.extraction_method,
            cvp.confidence_score,
            cvp.processed_at,
            cvp.created_at,
            c.full_name as candidate_name,
            c.email as candidate_email,
            d.original_filename as document_name,
            COUNT(cvl.log_id) as total_logs,
            COUNT(CASE WHEN cvl.log_level = 'ERROR' THEN 1 END) as error_logs,
            COUNT(CASE WHEN cvl.log_level = 'WARNING' THEN 1 END) as warning_logs
        FROM hh_cv_processing cvp
        JOIN hh_candidates c ON cvp.candidate_id = c.candidate_id
        LEFT JOIN hh_documents d ON cvp.document_id = d.document_id
        LEFT JOIN hh_cv_processing_logs cvl ON cvp.processing_id = cvl.processing_id
        GROUP BY cvp.processing_id, c.full_name, c.email, d.original_filename;
    """)
    
    # Vista de estadísticas de extracción por método
    op.execute("""
        CREATE OR REPLACE VIEW v_cv_extraction_stats AS
        SELECT 
            extraction_method,
            processing_status,
            COUNT(*) as total_count,
            AVG(confidence_score) as avg_confidence,
            AVG(extraction_duration_ms) as avg_duration_ms,
            AVG(pages_processed) as avg_pages,
            MIN(processed_at) as first_processed,
            MAX(processed_at) as last_processed
        FROM hh_cv_processing
        WHERE processed_at IS NOT NULL
        GROUP BY extraction_method, processing_status;
    """)


def downgrade():
    # Eliminar vistas
    op.execute("DROP VIEW IF EXISTS v_cv_extraction_stats")
    op.execute("DROP VIEW IF EXISTS v_cv_processing_summary")
    op.execute("DROP VIEW IF EXISTS v_candidates_cv_summary")
    
    # Eliminar triggers
    op.execute("DROP TRIGGER IF EXISTS trg_hh_cv_processing_updated_at ON hh_cv_processing")
    
    # Eliminar tablas en orden inverso (respetando FKs)
    op.drop_table('hh_cv_processing_logs')
    op.drop_table('hh_cv_versions')
    op.drop_table('hh_cv_processing')
    
    # Eliminar ENUMs
    op.execute("DROP TYPE IF EXISTS cvversionstatus")
    op.execute("DROP TYPE IF EXISTS processingstatus")
    op.execute("DROP TYPE IF EXISTS extractionmethod")
