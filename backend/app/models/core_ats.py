"""
Nuevo modelo de datos ATS - Core Models
Data Architecture según especificación exacta.
La tabla applications es la ENTIDAD CENTRAL.

NOTA: Tablas con prefijo 'hh_' para evitar colisiones con modelo anterior.
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
    """Etapas detalladas del pipeline de aplicación."""
    # Etapas iniciales
    SOURCING = "sourcing"                    # Recién ingresado
    SHORTLIST = "shortlist"                  # Pre-seleccionado
    TERNA = "terna"                          # En terna de 3 candidatos
    
    # Etapas de contacto
    CONTACT_PENDING = "contact_pending"      # Pendiente de contactar (necesita datos)
    CONTACTED = "contacted"                  # Contactado, esperando respuesta
    INTERESTED = "interested"                # Respondió positivamente
    NOT_INTERESTED = "not_interested"        # Respondió negativamente
    NO_RESPONSE = "no_response"              # No respondió (48-72h)
    
    # Etapas de entrevista
    INTERVIEW_SCHEDULED = "interview_scheduled"  # Entrevista agendada
    INTERVIEW_DONE = "interview_done"        # Entrevista realizada
    
    # Etapas de oferta
    OFFER_SENT = "offer_sent"                # Oferta enviada
    OFFER_ACCEPTED = "offer_accepted"        # Oferta aceptada
    OFFER_REJECTED = "offer_rejected"        # Oferta rechazada
    
    # Estados finales
    HIRED = "hired"                          # Contratado
    DISCARDED = "discarded"                  # Descartado por consultor


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
# MODELO 1: HH_CANDIDATES (Candidatos Headhunting)
# =============================================================================

class HHCandidate(Base):
    """
    Candidatos del sistema Headhunting.
    NOTA: Nunca guardar scores aquí. Los scores van en hh_assessment_scores.
    """
    __tablename__ = "hh_candidates"
    
    __table_args__ = (
        Index('idx_hh_candidates_email', 'email'),
        Index('idx_hh_candidates_national_id', 'national_id'),
        Index('idx_hh_candidates_name', 'full_name'),
        Index('idx_hh_candidates_created', 'created_at'),
        UniqueConstraint('national_id', name='uix_hh_candidates_national_id'),
    )
    
    candidate_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(Text, nullable=False)
    national_id = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    linkedin_url = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    applications = relationship("HHApplication", back_populates="candidate", cascade="all, delete-orphan")
    documents = relationship("HHDocument", back_populates="candidate", foreign_keys="HHDocument.candidate_id")
    communications = relationship(
        "Communication",
        back_populates="candidate",
        foreign_keys="Communication.candidate_id",
        cascade="all, delete-orphan"
    )


# =============================================================================
# MODELO 2: HH_CLIENTS (Clientes/Empresas)
# =============================================================================

class HHClient(Base):
    """Clientes o empresas que contratan headhunting."""
    __tablename__ = "hh_clients"
    
    __table_args__ = (
        Index('idx_hh_clients_name', 'client_name'),
    )
    
    client_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_name = Column(Text, nullable=False)
    industry = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    roles = relationship("HHRole", back_populates="client", cascade="all, delete-orphan")


# =============================================================================
# MODELO 3: HH_ROLES (Vacantes/Cargos)
# =============================================================================

class HHRole(Base):
    """Vacantes o roles a cubrir."""
    __tablename__ = "hh_roles"
    
    __table_args__ = (
        Index('idx_hh_roles_client', 'client_id'),
        Index('idx_hh_roles_status', 'status'),
        Index('idx_hh_roles_title', 'role_title'),
    )
    
    role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("hh_clients.client_id"), nullable=False)
    role_title = Column(Text, nullable=False)
    location = Column(Text, nullable=True)
    seniority = Column(Text, nullable=True)
    status = Column(SQLEnum(RoleStatus), default=RoleStatus.OPEN, nullable=False)
    date_opened = Column(Date, default=datetime.utcnow().date)
    date_closed = Column(Date, nullable=True)
    role_description_doc_id = Column(UUID(as_uuid=True), ForeignKey("hh_documents.document_id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    client = relationship("HHClient", back_populates="roles")
    applications = relationship("HHApplication", back_populates="role", cascade="all, delete-orphan")
    documents = relationship("HHDocument", back_populates="role", foreign_keys="HHDocument.role_id")
    role_description_doc = relationship("HHDocument", foreign_keys=[role_description_doc_id])


# =============================================================================
# MODELO 4: HH_APPLICATIONS (ENTIDAD CENTRAL)
# =============================================================================

class HHApplication(Base):
    """
    ENTIDAD CENTRAL: Postulación de candidato a una vacante.
    Aquí se almacena todo el proceso de selección.
    """
    __tablename__ = "hh_applications"
    
    __table_args__ = (
        Index('idx_hh_applications_candidate', 'candidate_id'),
        Index('idx_hh_applications_role', 'role_id'),
        Index('idx_hh_applications_stage', 'stage'),
        Index('idx_hh_applications_hired', 'hired'),
        Index('idx_hh_applications_score', 'overall_score'),
        UniqueConstraint('candidate_id', 'role_id', name='uix_hh_applications_candidate_role'),
    )
    
    application_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("hh_candidates.candidate_id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("hh_roles.role_id"), nullable=False)
    stage = Column(SQLEnum(ApplicationStage), default=ApplicationStage.SOURCING, nullable=False)
    hired = Column(Boolean, default=False)
    decision_date = Column(Date, nullable=True)
    overall_score = Column(Numeric(5, 2), CheckConstraint('overall_score >= 0 AND overall_score <= 100'), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Campos para el nuevo flujo de contacto
    discard_reason = Column(Text, nullable=True)  # Razón de descarte por consultor
    initial_contact_date = Column(DateTime, nullable=True)  # Fecha de contacto inicial
    candidate_response_date = Column(DateTime, nullable=True)  # Fecha de respuesta del candidato
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    candidate = relationship("HHCandidate", back_populates="applications")
    role = relationship("HHRole", back_populates="applications")
    documents = relationship("HHDocument", back_populates="application", foreign_keys="HHDocument.application_id")
    interviews = relationship("HHInterview", back_populates="application", cascade="all, delete-orphan")
    assessments = relationship("HHAssessment", back_populates="application", cascade="all, delete-orphan")
    flags = relationship("HHFlag", back_populates="application", cascade="all, delete-orphan")
    communications = relationship(
        "Communication",
        back_populates="application",
        foreign_keys="Communication.application_id",
        cascade="all, delete-orphan"
    )


# =============================================================================
# MODELO 5: HH_DOCUMENTS (Evidencia RAW)
# =============================================================================

class HHDocument(Base):
    """Documentos PDF/DOCX como evidencia. Solo referencias, no contenido."""
    __tablename__ = "hh_documents"
    
    __table_args__ = (
        Index('idx_hh_docs_application', 'application_id'),
        Index('idx_hh_docs_hash', 'sha256_hash'),
        Index('idx_hh_docs_type', 'doc_type'),
        UniqueConstraint('sha256_hash', name='uix_hh_documents_hash'),
    )
    
    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("hh_applications.application_id"), nullable=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("hh_roles.role_id"), nullable=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("hh_candidates.candidate_id"), nullable=True)
    doc_type = Column(SQLEnum(DocumentType), nullable=False)
    original_filename = Column(Text, nullable=False)
    storage_uri = Column(Text, nullable=False)
    sha256_hash = Column(Text, nullable=False)
    uploaded_by = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("HHApplication", back_populates="documents", foreign_keys=[application_id])
    role = relationship("HHRole", back_populates="documents", foreign_keys=[role_id])
    candidate = relationship("HHCandidate", back_populates="documents", foreign_keys=[candidate_id])
    interviews = relationship("HHInterview", back_populates="raw_document", foreign_keys="HHInterview.raw_doc_id")
    assessments = relationship("HHAssessment", back_populates="raw_document", foreign_keys="HHAssessment.raw_pdf_id")
    flags = relationship("HHFlag", back_populates="source_document", foreign_keys="HHFlag.source_doc_id")


# =============================================================================
# MODELO 6: HH_INTERVIEWS (Entrevistas)
# =============================================================================

class HHInterview(Base):
    """Notas y resumen de entrevistas."""
    __tablename__ = "hh_interviews"
    
    __table_args__ = (
        Index('idx_hh_interviews_application', 'application_id'),
    )
    
    interview_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("hh_applications.application_id"), nullable=False)
    interview_date = Column(DateTime, nullable=True)
    interviewer = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)
    raw_doc_id = Column(UUID(as_uuid=True), ForeignKey("hh_documents.document_id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("HHApplication", back_populates="interviews")
    raw_document = relationship("HHDocument", back_populates="interviews", foreign_keys=[raw_doc_id])


# =============================================================================
# MODELO 7: HH_ASSESSMENTS (Evaluaciones Psicométricas)
# =============================================================================

class HHAssessment(Base):
    """Evaluaciones psicométricas (Factor Oscuro, DISC, etc.)."""
    __tablename__ = "hh_assessments"
    
    __table_args__ = (
        Index('idx_hh_assessments_application', 'application_id'),
        Index('idx_hh_assessments_type', 'assessment_type'),
    )
    
    assessment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("hh_applications.application_id"), nullable=False)
    assessment_type = Column(SQLEnum(AssessmentType), nullable=False)
    assessment_date = Column(Date, nullable=True)
    sincerity_score = Column(Numeric(5, 2), CheckConstraint('sincerity_score >= 0 AND sincerity_score <= 100'), nullable=True)
    raw_pdf_id = Column(UUID(as_uuid=True), ForeignKey("hh_documents.document_id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("HHApplication", back_populates="assessments")
    raw_document = relationship("HHDocument", back_populates="assessments", foreign_keys=[raw_pdf_id])
    scores = relationship("HHAssessmentScore", back_populates="assessment", cascade="all, delete-orphan")


# =============================================================================
# MODELO 8: HH_ASSESSMENT_SCORES (SCORES DINÁMICOS - FILAS, NO COLUMNAS)
# =============================================================================

class HHAssessmentScore(Base):
    """
    SCORES DINÁMICOS: Cada dimensión es una fila.
    Ejemplo: ('Egocentrismo', 45), ('Volatilidad', 62)
    """
    __tablename__ = "hh_assessment_scores"
    
    __table_args__ = (
        Index('idx_hh_scores_assessment', 'assessment_id'),
        Index('idx_hh_scores_dimension', 'dimension'),
    )
    
    score_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("hh_assessments.assessment_id"), nullable=False)
    dimension = Column(Text, nullable=False)  # Ej: "Egocentrismo", "Seguimiento de Gestión"
    value = Column(Numeric(5, 2), CheckConstraint('value >= 0 AND value <= 100'), nullable=False)
    unit = Column(Text, default="score", nullable=False)
    source_page = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    assessment = relationship("HHAssessment", back_populates="scores")


# =============================================================================
# MODELO 9: HH_FLAGS (Riesgos y Alertas)
# =============================================================================

class HHFlag(Base):
    """Flags de riesgo detectados en cualquier etapa del proceso."""
    __tablename__ = "hh_flags"
    
    __table_args__ = (
        Index('idx_hh_flags_application', 'application_id'),
        Index('idx_hh_flags_severity', 'severity'),
        Index('idx_hh_flags_category', 'category'),
    )
    
    flag_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("hh_applications.application_id"), nullable=False)
    category = Column(Text, nullable=False)  # Ej: "riesgo_ego", "riesgo_conflicto"
    severity = Column(SQLEnum(FlagSeverity), nullable=False)
    evidence = Column(Text, nullable=True)
    source = Column(SQLEnum(FlagSource), nullable=False)
    source_doc_id = Column(UUID(as_uuid=True), ForeignKey("hh_documents.document_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("HHApplication", back_populates="flags")
    source_document = relationship("HHDocument", back_populates="flags", foreign_keys=[source_doc_id])


# =============================================================================
# MODELO 10: HH_AUDIT_LOG (Trazabilidad Completa)
# =============================================================================

class HHAuditLog(Base):
    """Registro de auditoría para trazabilidad total."""
    __tablename__ = "hh_audit_log"
    
    __table_args__ = (
        Index('idx_hh_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_hh_audit_changed_at', 'changed_at'),
    )
    
    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(Text, nullable=False)  # 'candidate', 'application', etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(SQLEnum(AuditAction), nullable=False)
    changed_by = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    diff_json = Column(JSONB, nullable=True)
