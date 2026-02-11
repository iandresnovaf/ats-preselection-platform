"""Modelos de base de datos."""
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, 
    Float, JSON, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    CONSULTANT = "consultant"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class User(Base):
    """Usuario del sistema (Admin o Consultor)."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50))  # WhatsApp number
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CONSULTANT)
    status = Column(SQLEnum(UserStatus), nullable=False, default=UserStatus.PENDING)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relations
    assigned_jobs = relationship("JobOpening", back_populates="assigned_consultant")
    decisions = relationship("CandidateDecision", back_populates="consultant")
    audit_logs = relationship("AuditLog", back_populates="user")


class Configuration(Base):
    """Configuración del sistema - almacena credenciales cifradas."""
    __tablename__ = "configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String(50), nullable=False, index=True)  # whatsapp, zoho, llm, email
    key = Column(String(100), nullable=False, index=True)
    value_encrypted = Column(Text, nullable=False)  # Valor cifrado
    is_encrypted = Column(Boolean, default=True)
    description = Column(String(500))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Para campos JSON complejos
    is_json = Column(Boolean, default=False)
    
    __table_args__ = (
        UniqueConstraint('category', 'key', name='uix_config_category_key'),
    )


class JobOpening(Base):
    """Oferta laboral."""
    __tablename__ = "job_openings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)  # Job Description (JD)
    department = Column(String(100))
    location = Column(String(255))
    seniority = Column(String(50))
    sector = Column(String(100))
    
    # Relación con consultor
    assigned_consultant_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assigned_consultant = relationship("User", back_populates="assigned_jobs")
    
    # Zoho integration
    zoho_job_id = Column(String(100))
    
    # Estado
    is_active = Column(Boolean, default=True)
    status = Column(String(50), default="draft")  # draft, published, closed
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    candidates = relationship("Candidate", back_populates="job_opening")


class CandidateStatus(str, Enum):
    NEW = "new"
    IN_REVIEW = "in_review"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    DISCARDED = "discarded"
    HIRED = "hired"


class Candidate(Base):
    """Candidato."""
    __tablename__ = "candidates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Datos de contacto
    email = Column(String(255), index=True)
    phone = Column(String(50), index=True)
    full_name = Column(String(255))
    
    # Normalización para anti-duplicados
    email_normalized = Column(String(255), index=True)
    phone_normalized = Column(String(50), index=True)
    
    # Datos extraídos del CV
    raw_data = Column(JSON)  # Datos JSON del CV original
    extracted_skills = Column(JSON)
    extracted_experience = Column(JSON)
    extracted_education = Column(JSON)
    
    # Relación
    job_opening_id = Column(UUID(as_uuid=True), ForeignKey("job_openings.id"))
    job_opening = relationship("JobOpening", back_populates="candidates")
    
    # Estado
    status = Column(SQLEnum(CandidateStatus), default=CandidateStatus.NEW)
    
    # Zoho integration
    zoho_candidate_id = Column(String(100))
    
    # Anti-duplicados
    duplicate_of_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    is_duplicate = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(50))  # webhook, cron, manual
    
    # Relations
    evaluations = relationship("Evaluation", back_populates="candidate")
    decisions = relationship("CandidateDecision", back_populates="candidate")
    communications = relationship("Communication", back_populates="candidate")


class Evaluation(Base):
    """Evaluación de candidato con IA."""
    __tablename__ = "evaluations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    candidate = relationship("Candidate", back_populates="evaluations")
    
    # Score y decisión
    score = Column(Float)  # 0-100
    decision = Column(String(20))  # PROCEED, REVIEW, REJECT_HARD
    
    # Detalles
    strengths = Column(JSON)
    gaps = Column(JSON)
    red_flags = Column(JSON)
    evidence = Column(Text)  # Fragmentos del CV que justifican el score
    
    # IA metadata
    llm_provider = Column(String(50))
    llm_model = Column(String(50))
    prompt_version = Column(String(20))
    
    # Filtros duros aplicados
    hard_filters_passed = Column(Boolean, default=True)
    hard_filters_failed = Column(JSON)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    evaluation_time_ms = Column(Integer)


class CandidateDecision(Base):
    """Decisión del consultor sobre un candidato."""
    __tablename__ = "candidate_decisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    candidate = relationship("Candidate", back_populates="decisions")
    
    consultant_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    consultant = relationship("User", back_populates="decisions")
    
    decision = Column(String(20))  # CONTINUE, DISCARD
    notes = Column(Text)
    
    # Sync status
    synced_to_zoho = Column(Boolean, default=False)
    synced_at = Column(DateTime)
    zoho_sync_error = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class CommunicationType(str, Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"


class CommunicationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Communication(Base):
    """Mensaje enviado al candidato."""
    __tablename__ = "communications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    candidate = relationship("Candidate", back_populates="communications")
    
    type = Column(SQLEnum(CommunicationType))
    status = Column(SQLEnum(CommunicationStatus), default=CommunicationStatus.PENDING)
    
    # Contenido
    template_name = Column(String(100))
    subject = Column(String(500))
    body = Column(Text)
    
    # Tracking
    external_message_id = Column(String(255))  # ID del proveedor (WhatsApp/Email)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """Log de auditoría."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    user = relationship("User", back_populates="audit_logs")
    
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, etc
    entity_type = Column(String(50))  # user, candidate, job, etc
    entity_id = Column(String(100))
    
    old_values = Column(JSON)
    new_values = Column(JSON)
    
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
