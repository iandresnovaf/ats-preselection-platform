"""
CV Extractions Table Migration
Revision ID: 20260217_1520_cv_extractions_table
Revises: 20260217_1511_cv_processing_tables
Create Date: 2026-02-17 15:20:00

Esta migración crea la tabla hh_cv_extractions para almacenar
datos extraídos de CVs por IA de forma simplificada.

Tabla: hh_cv_extractions
- Relacionada con hh_candidates (cada extracción pertenece a un candidato)
- Almacena texto raw, JSON estructurado y metadatos de extracción
- Incluye índices optimizados para búsquedas frecuentes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260217_1520_cv_extractions_table'
down_revision = '20260217_1511_cv_processing_tables'
branch_labels = None
depends_on = None


def upgrade():
    # =============================================================================
    # TABLA: HH_CV_EXTRACTIONS
    # =============================================================================
    op.create_table(
        'hh_cv_extractions',
        sa.Column('extraction_id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        # Contenido extraído
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('extracted_json', postgresql.JSONB(), nullable=True),
        # Método y calidad de extracción
        sa.Column(
            'extraction_method',
            sa.Enum('pdf_text', 'ocr', 'ai_extraction', 'hybrid', 'manual', name='extractionmethod'),
            nullable=True
        ),
        sa.Column(
            'confidence_score',
            sa.Numeric(5, 2),
            nullable=True
        ),
        # Información del archivo fuente
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('file_hash', sa.Text(), nullable=False),
        # Referencia opcional al documento
        sa.Column('document_id', sa.UUID(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        # Constraints
        sa.PrimaryKeyConstraint('extraction_id'),
        sa.ForeignKeyConstraint(['candidate_id'], ['hh_candidates.candidate_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['hh_documents.document_id'], ondelete='SET NULL'),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 100', name='chk_cv_extractions_confidence'),
        sa.UniqueConstraint('file_hash', name='uix_hh_cv_extractions_file_hash')
    )

    # =============================================================================
    # ÍNDICES OPTIMIZADOS
    # =============================================================================

    # Índice para búsquedas por candidato (más frecuente)
    op.create_index(
        'idx_hh_cv_extractions_candidate',
        'hh_cv_extractions',
        ['candidate_id']
    )

    # Índice para filtrar por método de extracción
    op.create_index(
        'idx_hh_cv_extractions_method',
        'hh_cv_extractions',
        ['extraction_method']
    )

    # Índice para búsquedas por score de confianza
    op.create_index(
        'idx_hh_cv_extractions_score',
        'hh_cv_extractions',
        ['confidence_score']
    )

    # Índice único para búsquedas por hash de archivo
    op.create_index(
        'idx_hh_cv_extractions_file_hash',
        'hh_cv_extractions',
        ['file_hash']
    )

    # Índice para ordenar por fecha de creación
    op.create_index(
        'idx_hh_cv_extractions_created',
        'hh_cv_extractions',
        ['created_at']
    )

    # Índice para búsquedas por nombre de archivo
    op.create_index(
        'idx_hh_cv_extractions_filename',
        'hh_cv_extractions',
        ['filename']
    )

    # Índice GIN para búsquedas en el JSONB de datos extraídos
    op.create_index(
        'idx_hh_cv_extractions_json_gin',
        'hh_cv_extractions',
        ['extracted_json'],
        postgresql_using='gin'
    )

    # Índice compuesto para búsquedas frecuentes: candidato + método
    op.create_index(
        'idx_hh_cv_extractions_candidate_method',
        'hh_cv_extractions',
        ['candidate_id', 'extraction_method']
    )

    # =============================================================================
    # TRIGGER PARA ACTUALIZAR updated_at
    # =============================================================================
    op.execute("""
        CREATE TRIGGER trg_hh_cv_extractions_updated_at
            BEFORE UPDATE ON hh_cv_extractions
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # =============================================================================
    # VISTAS ÚTILES
    # =============================================================================

    # Vista de extracciones por candidato con última versión
    op.execute("""
        CREATE OR REPLACE VIEW v_candidate_cv_extractions AS
        SELECT 
            c.candidate_id,
            c.full_name as candidate_name,
            c.email as candidate_email,
            ce.extraction_id,
            ce.filename,
            ce.file_hash,
            ce.extraction_method,
            ce.confidence_score,
            ce.created_at as extraction_date,
            ce.extracted_json,
            CASE 
                WHEN ce.confidence_score >= 80 THEN 'high'
                WHEN ce.confidence_score >= 50 THEN 'medium'
                ELSE 'low'
            END as confidence_level
        FROM hh_candidates c
        LEFT JOIN hh_cv_extractions ce ON ce.candidate_id = c.candidate_id;
    """)

    # Vista de estadísticas de extracción por método
    op.execute("""
        CREATE OR REPLACE VIEW v_cv_extraction_stats_simple AS
        SELECT 
            extraction_method,
            COUNT(*) as total_extractions,
            AVG(confidence_score) as avg_confidence,
            MIN(confidence_score) as min_confidence,
            MAX(confidence_score) as max_confidence,
            COUNT(CASE WHEN confidence_score >= 80 THEN 1 END) as high_confidence_count,
            COUNT(CASE WHEN confidence_score < 50 THEN 1 END) as low_confidence_count,
            MIN(created_at) as first_extraction,
            MAX(created_at) as last_extraction
        FROM hh_cv_extractions
        GROUP BY extraction_method;
    """)

    # Vista de candidatos con CVs extraídos
    op.execute("""
        CREATE OR REPLACE VIEW v_candidates_with_cv_extraction AS
        SELECT 
            c.candidate_id,
            c.full_name,
            c.email,
            c.phone,
            ce.extraction_id,
            ce.confidence_score,
            ce.extraction_method,
            ce.filename,
            ce.created_at as extracted_at,
            ce.extracted_json->>'nombre' as extracted_name,
            ce.extracted_json->>'email' as extracted_email,
            ce.extracted_json->>'telefono' as extracted_phone,
            ce.extracted_json->>'titulo_profesional' as extracted_title,
            ce.extracted_json->>'ubicacion' as extracted_location
        FROM hh_candidates c
        INNER JOIN hh_cv_extractions ce ON ce.candidate_id = c.candidate_id
        ORDER BY ce.created_at DESC;
    """)


def downgrade():
    # Eliminar vistas
    op.execute("DROP VIEW IF EXISTS v_candidates_with_cv_extraction")
    op.execute("DROP VIEW IF EXISTS v_cv_extraction_stats_simple")
    op.execute("DROP VIEW IF EXISTS v_candidate_cv_extractions")

    # Eliminar trigger
    op.execute("DROP TRIGGER IF EXISTS trg_hh_cv_extractions_updated_at ON hh_cv_extractions")

    # Eliminar índices
    op.drop_index('idx_hh_cv_extractions_candidate_method', table_name='hh_cv_extractions')
    op.drop_index('idx_hh_cv_extractions_json_gin', table_name='hh_cv_extractions')
    op.drop_index('idx_hh_cv_extractions_filename', table_name='hh_cv_extractions')
    op.drop_index('idx_hh_cv_extractions_created', table_name='hh_cv_extractions')
    op.drop_index('idx_hh_cv_extractions_file_hash', table_name='hh_cv_extractions')
    op.drop_index('idx_hh_cv_extractions_score', table_name='hh_cv_extractions')
    op.drop_index('idx_hh_cv_extractions_method', table_name='hh_cv_extractions')
    op.drop_index('idx_hh_cv_extractions_candidate', table_name='hh_cv_extractions')

    # Eliminar tabla
    op.drop_table('hh_cv_extractions')
