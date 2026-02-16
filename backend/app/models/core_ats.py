"""
Nuevo modelo de datos ATS - Core Models
Data Architecture según especificación exacta.
La tabla applications es la ENTIDAD CENTRAL.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, 
    Numeric, JSON, Date, Enum as SQLEnum, UniqueConstraint, CheckConstraint,
    Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


# =============================================================================
# ENUMS
# =============================================================================

class RoleStatus(str, Enum):
    """Estados posibles de una vacante/rol."""
    OPEN = "open"
    HOLD = "hold"
    CLOSED = "closed"


class ApplicationStage(str, Enum):
    """Etapas del pipeline de aplicación."""
    SOURCING = "sourcing"
    SHORTLIST = "shortlist"
    TERNA = "terna"
    INTERVIEW = "interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"


class DocumentType(str, Enum):
    """Tipos de documentos."""
    CV = "cv"
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    ROLE_PROFILE = "role_profile"
    OTHER = "other"


class AssessmentType(str, Enum):
    """Tipos de evaluaciones psicométricas."""
    FACTOR_OSCURO = "factor_oscuro"
    INTELIGENCIA_EJECUTIVA = "inteligencia_ejecutiva"
    KOMPEDISC = "kompedisc"
    OTHER = "other"


class FlagSeverity(str, Enum):
    """Niveles de severidad para flags/alertas."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FlagSource(str, Enum):
    """Fuentes de origen para flags."""
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    CV = "cv"


class AuditAction(str, Enum):
    """Acciones de auditoría."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


# =============================================================================
# MODELO 1: CANDIDATES
# =============================================================================

class Candidate(Base):
    """
    Candidatos del sistema.
    NOTA: Nunca guardar scores aquí. Los scores van en assessment_scores vía assessments→applications.
    """
    __tablename__ = "candidates"
    
    __table_args__ = (
        # Índices optimizados para búsquedas frecuentes
        Index('idx_candidates_email', 'email'),
        Index('idx_candidates_national_id', 'national_id'),
        Index('idx_candidates_name_search', 'full_name'),
        Index('idx_candidates_created_at', 'created_at'),
        # Constraints
        UniqueConstraint('national_id', name='uix_candidates_national_id'),
    )
    
    candidate_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(Text, nullable=False)
    national_id = Column(Text, nullable=True)  # Cedula/DNI/Pasaporte
    email = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    linkedin_url = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="candidate", foreign_keys="Document.candidate_id")


# =============================================================================
# MODELO 2: CLIENTS
# =============================================================================

class Client(Base):
    """Clientes/empresas que publican vacantes."""
    __tablename__ = "clients"
    
    __table_args__ = (
        Index('idx_clients_name', 'client_name'),
        Index('idx_clients_created_at', 'created_at'),
    )
    
    client_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_name = Column(Text, nullable=False)
    industry = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    roles = relationship("Role", back_populates="client", cascade="all, delete-orphan")


# =============================================================================
# MODELO 3: ROLES (VACANTES)
# =============================================================================

class Role(Base):
    """
    Vacantes/roles disponibles.
    NOTA: El documento de descripción del rol es opcional.
    """
    __tablename__ = "roles"
    
    __table_args__ = (
        Index('idx_roles_client_id', 'client_id'),
        Index('idx_roles_status', 'status'),
        Index('idx_roles_date_opened', 'date_opened'),
        Index('idx_roles_location', 'location'),
        Index('idx_roles_seniority', 'seniority'),
        Index('idx_roles_status_opened', 'status', 'date_opened'),
    )
    
    role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.client_id"), nullable=False)
    role_title = Column(Text, nullable=False)
    location = Column(Text, nullable=True)
    seniority = Column(Text, nullable=True)
    status = Column(SQLEnum(RoleStatus), nullable=False, default=RoleStatus.OPEN)
    date_opened = Column(Date, nullable=True)
    date_closed = Column(Date, nullable=True)
    role_description_doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="roles")
    applications = relationship("Application", back_populates="role", cascade="all, delete-orphan")
    role_description_doc = relationship("Document", foreign_keys=[role_description_doc_id], post_update=True)
    documents = relationship("Document", back_populates="role", foreign_keys="Document.role_id")


# =============================================================================
# MODELO 4: APPLICATIONS (ENTIDAD CENTRAL)
# =============================================================================

class Application(Base):
    """
    ENTIDAD CENTRAL: Conexión Candidato ↔ Vacante
    Toda la información de pipeline, scores y decisiones se conecta aquí.
    """
    __tablename__ = "applications"
    
    __table_args__ = (
        # Constraint único: un candidato solo puede aplicar una vez a cada vacante
        UniqueConstraint('candidate_id', 'role_id', name='uix_applications_candidate_role'),
        # Índices optimizados
        Index('idx_applications_candidate_id', 'candidate_id'),
        Index('idx_applications_role_id', 'role_id'),
        Index('idx_applications_stage', 'stage'),
        Index('idx_applications_hired', 'hired'),
        Index('idx_applications_role_stage', 'role_id', 'stage'),
        Index('idx_applications_candidate_hired', 'candidate_id', 'hired'),
        Index('idx_applications_decision_date', 'decision_date'),
        Index('idx_applications_overall_score', 'overall_score'),
    )
    
    application_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.candidate_id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.role_id"), nullable=False)
    stage = Column(SQLEnum(ApplicationStage), nullable=False, default=ApplicationStage.SOURCING)
    hired = Column(Boolean, nullable=False, default=False)
    decision_date = Column(Date, nullable=True)
    overall_score = Column(Numeric(5, 2), nullable=True)  # Score general 0-100
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="applications")
    role = relationship("Role", back_populates="applications")
    documents = relationship("Document", back_populates="application", foreign_keys="Document.application_id")
    interviews = relationship("Interview", back_populates="application", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="application", cascade="all, delete-orphan")
    flags = relationship("Flag", back_populates="application", cascade="all, delete-orphan")


# =============================================================================
# MODELO 5: DOCUMENTS (EVIDENCIA RAW)
# =============================================================================

class Document(Base):
    """
    Documentos/evidencia del proceso.
    Puede estar asociado a application, role, o candidate (o combinación).
    """
    __tablename__ = "documents"
    
    __table_args__ = (
        Index('idx_documents_application_id', 'application_id'),
        Index('idx_documents_role_id', 'role_id'),
        Index('idx_documents_candidate_id', 'candidate_id'),
        Index('idx_documents_doc_type', 'doc_type'),
        Index('idx_documents_uploaded_at', 'uploaded_at'),
        Index('idx_documents_sha256', 'sha256_hash'),
    )
    
    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.application_id"), nullable=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.role_id"), nullable=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.candidate_id"), nullable=True)
    doc_type = Column(SQLEnum(DocumentType), nullable=False)
    original_filename = Column(Text, nullable=False)
    storage_uri = Column(Text, nullable=False)  # URL/path de almacenamiento
    sha256_hash = Column(Text, nullable=True)   # Para verificación de integridad
    uploaded_by = Column(Text, nullable=True)   # Email o ID del usuario
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="documents", foreign_keys=[application_id])
    role = relationship("Role", back_populates="documents", foreign_keys=[role_id])
    candidate = relationship("Candidate", back_populates="documents", foreign_keys=[candidate_id])
    interviews = relationship("Interview", back_populates="raw_document", foreign_keys="Interview.raw_doc_id")
    assessments = relationship("Assessment", back_populates="raw_document", foreign_keys="Assessment.raw_pdf_id")
    flags = relationship("Flag", back_populates="source_document", foreign_keys="Flag.source_doc_id")


# =============================================================================
# MODELO 6: INTERVIEWS
# =============================================================================

class Interview(Base):
    """Entrevistas realizadas a candidatos."""
    __tablename__ = "interviews"
    
    __table_args__ = (
        Index('idx_interviews_application_id', 'application_id'),
        Index('idx_interviews_date', 'interview_date'),
        Index('idx_interviews_interviewer', 'interviewer'),
    )
    
    interview_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.application_id"), nullable=False)
    interview_date = Column(DateTime, nullable=True)
    interviewer = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)
    raw_doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="interviews")
    raw_document = relationship("Document", back_populates="interviews", foreign_keys=[raw_doc_id])


# =============================================================================
# MODELO 7: ASSESSMENTS
# =============================================================================

class Assessment(Base):
    """
    Evaluaciones psicométricas aplicadas.
    Los scores individuales van en assessment_scores (diseño dinámico).
    """
    __tablename__ = "assessments"
    
    __table_args__ = (
        Index('idx_assessments_application_id', 'application_id'),
        Index('idx_assessments_type', 'assessment_type'),
        Index('idx_assessments_date', 'assessment_date'),
        Index('idx_assessments_app_type', 'application_id', 'assessment_type'),
    )
    
    assessment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.application_id"), nullable=False)
    assessment_type = Column(SQLEnum(AssessmentType), nullable=False)
    assessment_date = Column(Date, nullable=True)
    sincerity_score = Column(Numeric(5, 2), nullable=True)  # Score de sinceridad 0-100
    raw_pdf_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="assessments")
    raw_document = relationship("Document", back_populates="assessments", foreign_keys=[raw_pdf_id])
    scores = relationship("AssessmentScore", back_populates="assessment", cascade="all, delete-orphan")


# =============================================================================
# MODELO 8: ASSESSMENT_SCORES (SCORES DINÁMICOS)
# =============================================================================

class AssessmentScore(Base):
    """
    Scores dinámicos de evaluaciones.
    NO hay columnas fijas - cada dimensión es una fila.
    Esto permite soportar cualquier tipo de evaluación sin cambiar el schema.
    """
    __tablename__ = "assessment_scores"
    
    __table_args__ = (
        # Constraint: valor debe estar entre 0 y 100
        CheckConstraint('value >= 0 AND value <= 100', name='chk_score_value_range'),
        Index('idx_assessment_scores_assessment_id', 'assessment_id'),
        Index('idx_assessment_scores_dimension', 'dimension'),
        Index('idx_assessment_scores_assessment_dimension', 'assessment_id', 'dimension'),
    )
    
    score_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.assessment_id"), nullable=False)
    dimension = Column(Text, nullable=False)  # Ej: "liderazgo", "trabajo_equipo", "integridad"
    value = Column(Numeric(5, 2), nullable=False)  # Valor 0-100
    unit = Column(Text, nullable=False, default='score')  # 'score', 'percentile', 'stanine'
    source_page = Column(Integer, nullable=True)  # Página del PDF origen
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    assessment = relationship("Assessment", back_populates="scores")


# =============================================================================
# MODELO 9: FLAGS (RIESGOS/ALERTAS)
# =============================================================================

class Flag(Base):
    """Flags/alertas de riesgo sobre candidatos."""
    __tablename__ = "flags"
    
    __table_args__ = (
        Index('idx_flags_application_id', 'application_id'),
        Index('idx_flags_severity', 'severity'),
        Index('idx_flags_category', 'category'),
        Index('idx_flags_source', 'source'),
        Index('idx_flags_app_severity', 'application_id', 'severity'),
        Index('idx_flags_created_at', 'created_at'),
    )
    
    flag_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.application_id"), nullable=False)
    category = Column(Text, nullable=True)  # Ej: "inconsistencia_cv", "riesgo_psicometrico"
    severity = Column(SQLEnum(FlagSeverity), nullable=False)
    evidence = Column(Text, nullable=True)  # Descripción/evidencia
    source = Column(SQLEnum(FlagSource), nullable=False)
    source_doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="flags")
    source_document = relationship("Document", back_populates="flags", foreign_keys=[source_doc_id])


# =============================================================================
# MODELO 10: AUDIT_LOG (TRAZABILIDAD)
# =============================================================================

class AuditLog(Base):
    """Log de auditoría para trazabilidad completa."""
    __tablename__ = "audit_logs"
    
    __table_args__ = (
        Index('idx_audit_logs_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_changed_by', 'changed_by'),
        Index('idx_audit_logs_changed_at', 'changed_at'),
        Index('idx_audit_logs_entity_action', 'entity_type', 'action'),
    )
    
    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(Text, nullable=False)  # 'candidate', 'application', 'role', etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(SQLEnum(AuditAction), nullable=False)
    changed_by = Column(Text, nullable=True)  # Email o ID del usuario
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    diff_json = Column(JSONB, nullable=True)  # Cambios en formato JSON


# =============================================================================
# VISTAS ÚTILES (opcional, se pueden crear via migration)
# =============================================================================

# Nota: Las vistas se crearán en la migración para no depender de
# características específicas de PostgreSQL en el modelo
