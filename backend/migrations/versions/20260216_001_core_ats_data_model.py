"""
Core ATS Migration - Modelo de datos completo
Revision ID: 20260216_001_core_ats_data_model
Revises: 20260212_001_matching_ia
Create Date: 2026-02-16 18:30:00

Esta migración implementa el modelo de datos Core ATS siguiendo EXACTAMENTE el diseño:
- candidates: Candidatos
- clients: Clientes
- roles: Vacantes
- applications: ENTIDAD CENTRAL (Candidato ↔ Vacante)
- documents: Evidencia RAW
- interviews: Entrevistas
- assessments: Evaluaciones psicométricas
- assessment_scores: Scores dinámicos (NO columnas fijas)
- flags: Riesgos/alertas
- audit_log: Trazabilidad

NOTA CRÍTICA: La tabla applications es la entidad central.
Nunca guardar scores en candidates.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260216_001_core_ats_data_model'
down_revision = '20260212_001_matching_ia'
branch_labels = None
depends_on = None


def upgrade():
    # =============================================================================
    # ENUMS
    # =============================================================================
    
    # RoleStatus enum
    rolestatus = postgresql.ENUM('open', 'hold', 'closed', name='rolestatus')
    rolestatus.create(op.get_bind())
    
    # ApplicationStage enum
    applicationstage = postgresql.ENUM('sourcing', 'shortlist', 'terna', 'interview', 'offer', 'hired', 'rejected', name='applicationstage')
    applicationstage.create(op.get_bind())
    
    # DocumentType enum
    documenttype = postgresql.ENUM('cv', 'interview', 'assessment', 'role_profile', 'other', name='documenttype')
    documenttype.create(op.get_bind())
    
    # AssessmentType enum
    assessmenttype = postgresql.ENUM('factor_oscuro', 'inteligencia_ejecutiva', 'kompedisc', 'other', name='assessmenttype')
    assessmenttype.create(op.get_bind())
    
    # FlagSeverity enum
    flagseverity = postgresql.ENUM('low', 'medium', 'high', name='flagseverity')
    flagseverity.create(op.get_bind())
    
    # FlagSource enum
    flagsource = postgresql.ENUM('interview', 'assessment', 'cv', name='flagsource')
    flagsource.create(op.get_bind())
    
    # AuditAction enum
    auditaction = postgresql.ENUM('create', 'update', 'delete', name='auditaction')
    auditaction.create(op.get_bind())
    
    # =============================================================================
    # TABLA 1: CANDIDATES
    # =============================================================================
    op.create_table(
        'candidates',
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('full_name', sa.Text(), nullable=False),
        sa.Column('national_id', sa.Text(), nullable=True),
        sa.Column('email', sa.Text(), nullable=True),
        sa.Column('phone', sa.Text(), nullable=True),
        sa.Column('location', sa.Text(), nullable=True),
        sa.Column('linkedin_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('candidate_id'),
        sa.UniqueConstraint('national_id', name='uix_candidates_national_id')
    )
    
    # Índices para candidates
    op.create_index('idx_candidates_email', 'candidates', ['email'])
    op.create_index('idx_candidates_national_id', 'candidates', ['national_id'])
    op.create_index('idx_candidates_name_search', 'candidates', ['full_name'])
    op.create_index('idx_candidates_created_at', 'candidates', ['created_at'])
    
    # =============================================================================
    # TABLA 2: CLIENTS
    # =============================================================================
    op.create_table(
        'clients',
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('client_name', sa.Text(), nullable=False),
        sa.Column('industry', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('client_id')
    )
    
    # Índices para clients
    op.create_index('idx_clients_name', 'clients', ['client_name'])
    op.create_index('idx_clients_created_at', 'clients', ['created_at'])
    
    # =============================================================================
    # TABLA 3: ROLES (VACANTES)
    # =============================================================================
    # Nota: documents se crea después, así que la FK a role_description_doc_id
    # se agregará más tarde
    op.create_table(
        'roles',
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('role_title', sa.Text(), nullable=False),
        sa.Column('location', sa.Text(), nullable=True),
        sa.Column('seniority', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('open', 'hold', 'closed', name='rolestatus'), nullable=False, server_default='open'),
        sa.Column('date_opened', sa.Date(), nullable=True),
        sa.Column('date_closed', sa.Date(), nullable=True),
        sa.Column('role_description_doc_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['client_id'], ['clients.client_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id')
    )
    
    # Índices para roles
    op.create_index('idx_roles_client_id', 'roles', ['client_id'])
    op.create_index('idx_roles_status', 'roles', ['status'])
    op.create_index('idx_roles_date_opened', 'roles', ['date_opened'])
    op.create_index('idx_roles_location', 'roles', ['location'])
    op.create_index('idx_roles_seniority', 'roles', ['seniority'])
    op.create_index('idx_roles_status_opened', 'roles', ['status', 'date_opened'])
    
    # =============================================================================
    # TABLA 4: APPLICATIONS (ENTIDAD CENTRAL)
    # =============================================================================
    op.create_table(
        'applications',
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('stage', sa.Enum('sourcing', 'shortlist', 'terna', 'interview', 'offer', 'hired', 'rejected', name='applicationstage'), nullable=False, server_default='sourcing'),
        sa.Column('hired', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('decision_date', sa.Date(), nullable=True),
        sa.Column('overall_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.candidate_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('application_id'),
        sa.UniqueConstraint('candidate_id', 'role_id', name='uix_applications_candidate_role')
    )
    
    # Índices para applications
    op.create_index('idx_applications_candidate_id', 'applications', ['candidate_id'])
    op.create_index('idx_applications_role_id', 'applications', ['role_id'])
    op.create_index('idx_applications_stage', 'applications', ['stage'])
    op.create_index('idx_applications_hired', 'applications', ['hired'])
    op.create_index('idx_applications_role_stage', 'applications', ['role_id', 'stage'])
    op.create_index('idx_applications_candidate_hired', 'applications', ['candidate_id', 'hired'])
    op.create_index('idx_applications_decision_date', 'applications', ['decision_date'])
    op.create_index('idx_applications_overall_score', 'applications', ['overall_score'])
    
    # =============================================================================
    # TABLA 5: DOCUMENTS (EVIDENCIA RAW)
    # =============================================================================
    op.create_table(
        'documents',
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=True),
        sa.Column('role_id', sa.UUID(), nullable=True),
        sa.Column('candidate_id', sa.UUID(), nullable=True),
        sa.Column('doc_type', sa.Enum('cv', 'interview', 'assessment', 'role_profile', 'other', name='documenttype'), nullable=False),
        sa.Column('original_filename', sa.Text(), nullable=False),
        sa.Column('storage_uri', sa.Text(), nullable=False),
        sa.Column('sha256_hash', sa.Text(), nullable=True),
        sa.Column('uploaded_by', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['application_id'], ['applications.application_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.candidate_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('document_id')
    )
    
    # Índices para documents
    op.create_index('idx_documents_application_id', 'documents', ['application_id'])
    op.create_index('idx_documents_role_id', 'documents', ['role_id'])
    op.create_index('idx_documents_candidate_id', 'documents', ['candidate_id'])
    op.create_index('idx_documents_doc_type', 'documents', ['doc_type'])
    op.create_index('idx_documents_uploaded_at', 'documents', ['uploaded_at'])
    op.create_index('idx_documents_sha256', 'documents', ['sha256_hash'])
    
    # Ahora agregamos la FK de role_description_doc_id en roles
    op.create_foreign_key(
        'fk_roles_description_doc',
        'roles', 'documents',
        ['role_description_doc_id'], ['document_id'],
        ondelete='SET NULL'
    )
    
    # =============================================================================
    # TABLA 6: INTERVIEWS
    # =============================================================================
    op.create_table(
        'interviews',
        sa.Column('interview_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('interview_date', sa.DateTime(), nullable=True),
        sa.Column('interviewer', sa.Text(), nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('raw_doc_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['application_id'], ['applications.application_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['raw_doc_id'], ['documents.document_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('interview_id')
    )
    
    # Índices para interviews
    op.create_index('idx_interviews_application_id', 'interviews', ['application_id'])
    op.create_index('idx_interviews_date', 'interviews', ['interview_date'])
    op.create_index('idx_interviews_interviewer', 'interviews', ['interviewer'])
    
    # =============================================================================
    # TABLA 7: ASSESSMENTS
    # =============================================================================
    op.create_table(
        'assessments',
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('assessment_type', sa.Enum('factor_oscuro', 'inteligencia_ejecutiva', 'kompedisc', 'other', name='assessmenttype'), nullable=False),
        sa.Column('assessment_date', sa.Date(), nullable=True),
        sa.Column('sincerity_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('raw_pdf_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['application_id'], ['applications.application_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['raw_pdf_id'], ['documents.document_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('assessment_id')
    )
    
    # Índices para assessments
    op.create_index('idx_assessments_application_id', 'assessments', ['application_id'])
    op.create_index('idx_assessments_type', 'assessments', ['assessment_type'])
    op.create_index('idx_assessments_date', 'assessments', ['assessment_date'])
    op.create_index('idx_assessments_app_type', 'assessments', ['application_id', 'assessment_type'])
    
    # =============================================================================
    # TABLA 8: ASSESSMENT_SCORES (SCORES DINÁMICOS - NO COLUMNAS FIJAS)
    # =============================================================================
    op.create_table(
        'assessment_scores',
        sa.Column('score_id', sa.UUID(), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('dimension', sa.Text(), nullable=False),
        sa.Column('value', sa.Numeric(5, 2), nullable=False),
        sa.Column('unit', sa.Text(), nullable=False, server_default='score'),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.assessment_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('score_id'),
        sa.CheckConstraint('value >= 0 AND value <= 100', name='chk_score_value_range')
    )
    
    # Índices para assessment_scores
    op.create_index('idx_assessment_scores_assessment_id', 'assessment_scores', ['assessment_id'])
    op.create_index('idx_assessment_scores_dimension', 'assessment_scores', ['dimension'])
    op.create_index('idx_assessment_scores_assessment_dimension', 'assessment_scores', ['assessment_id', 'dimension'])
    
    # =============================================================================
    # TABLA 9: FLAGS (RIESGOS/ALERTAS)
    # =============================================================================
    op.create_table(
        'flags',
        sa.Column('flag_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('category', sa.Text(), nullable=True),
        sa.Column('severity', sa.Enum('low', 'medium', 'high', name='flagseverity'), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('source', sa.Enum('interview', 'assessment', 'cv', name='flagsource'), nullable=False),
        sa.Column('source_doc_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['application_id'], ['applications.application_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_doc_id'], ['documents.document_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('flag_id')
    )
    
    # Índices para flags
    op.create_index('idx_flags_application_id', 'flags', ['application_id'])
    op.create_index('idx_flags_severity', 'flags', ['severity'])
    op.create_index('idx_flags_category', 'flags', ['category'])
    op.create_index('idx_flags_source', 'flags', ['source'])
    op.create_index('idx_flags_app_severity', 'flags', ['application_id', 'severity'])
    op.create_index('idx_flags_created_at', 'flags', ['created_at'])
    
    # =============================================================================
    # TABLA 10: AUDIT_LOG (TRAZABILIDAD)
    # =============================================================================
    op.create_table(
        'audit_logs',
        sa.Column('audit_id', sa.UUID(), nullable=False),
        sa.Column('entity_type', sa.Text(), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('action', sa.Enum('create', 'update', 'delete', name='auditaction'), nullable=False),
        sa.Column('changed_by', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('diff_json', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('audit_id')
    )
    
    # Índices para audit_logs
    op.create_index('idx_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_changed_by', 'audit_logs', ['changed_by'])
    op.create_index('idx_audit_logs_changed_at', 'audit_logs', ['changed_at'])
    op.create_index('idx_audit_logs_entity_action', 'audit_logs', ['entity_type', 'action'])
    
    # =============================================================================
    # TRIGGER para actualizar updated_at automáticamente
    # =============================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Aplicar trigger a todas las tablas con updated_at
    tables_with_updated_at = [
        'candidates', 'clients', 'roles', 'applications',
        'interviews', 'assessments'
    ]
    
    for table in tables_with_updated_at:
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)
    
    # =============================================================================
    # VISTAS ÚTILES
    # =============================================================================
    
    # Vista de aplicaciones con resumen
    op.execute("""
        CREATE OR REPLACE VIEW v_applications_summary AS
        SELECT 
            a.application_id,
            a.candidate_id,
            a.role_id,
            a.stage,
            a.hired,
            a.overall_score,
            a.created_at,
            a.updated_at,
            c.full_name as candidate_name,
            c.email as candidate_email,
            r.role_title,
            cl.client_name,
            COUNT(DISTINCT i.interview_id) as interview_count,
            COUNT(DISTINCT ass.assessment_id) as assessment_count,
            COUNT(DISTINCT f.flag_id) as flag_count,
            COUNT(DISTINCT CASE WHEN f.severity = 'high' THEN f.flag_id END) as high_flag_count
        FROM applications a
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN roles r ON a.role_id = r.role_id
        JOIN clients cl ON r.client_id = cl.client_id
        LEFT JOIN interviews i ON a.application_id = i.application_id
        LEFT JOIN assessments ass ON a.application_id = ass.application_id
        LEFT JOIN flags f ON a.application_id = f.application_id
        GROUP BY a.application_id, c.full_name, c.email, r.role_title, cl.client_name;
    """)
    
    # Vista de roles con conteos
    op.execute("""
        CREATE OR REPLACE VIEW v_roles_summary AS
        SELECT 
            r.role_id,
            r.role_title,
            r.location,
            r.seniority,
            r.status,
            r.date_opened,
            r.date_closed,
            r.created_at,
            cl.client_id,
            cl.client_name,
            COUNT(DISTINCT a.application_id) as total_applications,
            COUNT(DISTINCT CASE WHEN a.stage = 'hired' THEN a.application_id END) as hired_count,
            COUNT(DISTINCT CASE WHEN a.hired = false AND a.stage = 'rejected' THEN a.application_id END) as rejected_count
        FROM roles r
        JOIN clients cl ON r.client_id = cl.client_id
        LEFT JOIN applications a ON r.role_id = a.role_id
        GROUP BY r.role_id, cl.client_id, cl.client_name;
    """)
    
    # Vista de candidatos con historial
    op.execute("""
        CREATE OR REPLACE VIEW v_candidates_summary AS
        SELECT 
            c.candidate_id,
            c.full_name,
            c.email,
            c.phone,
            c.location,
            c.created_at,
            COUNT(DISTINCT a.application_id) as total_applications,
            COUNT(DISTINCT CASE WHEN a.hired = true THEN a.application_id END) as hired_count,
            MAX(a.decision_date) as last_decision_date
        FROM candidates c
        LEFT JOIN applications a ON c.candidate_id = a.candidate_id
        GROUP BY c.candidate_id;
    """)


def downgrade():
    # Eliminar vistas
    op.execute("DROP VIEW IF EXISTS v_candidates_summary")
    op.execute("DROP VIEW IF EXISTS v_roles_summary")
    op.execute("DROP VIEW IF EXISTS v_applications_summary")
    
    # Eliminar triggers
    tables_with_updated_at = [
        'candidates', 'clients', 'roles', 'applications',
        'interviews', 'assessments'
    ]
    for table in tables_with_updated_at:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
    
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Eliminar tablas en orden inverso (respetando FKs)
    op.drop_table('audit_logs')
    op.drop_table('flags')
    op.drop_table('assessment_scores')
    op.drop_table('assessments')
    op.drop_table('interviews')
    op.drop_table('documents')
    op.drop_table('applications')
    op.drop_table('roles')
    op.drop_table('clients')
    op.drop_table('candidates')
    
    # Eliminar ENUMs
    op.execute("DROP TYPE IF EXISTS auditaction")
    op.execute("DROP TYPE IF EXISTS flagsource")
    op.execute("DROP TYPE IF EXISTS flagseverity")
    op.execute("DROP TYPE IF EXISTS assessmenttype")
    op.execute("DROP TYPE IF EXISTS documenttype")
    op.execute("DROP TYPE IF EXISTS applicationstage")
    op.execute("DROP TYPE IF EXISTS rolestatus")
