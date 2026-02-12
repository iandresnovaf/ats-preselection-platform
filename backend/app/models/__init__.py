"""Modelos de base de datos."""
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, 
    Float, Numeric, JSON, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    CONSULTANT = "consultant"
    VIEWER = "viewer"  # Solo lectura - puede ver jobs, candidates, submissions


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


# Importar modelos modulares (deben definirse después de Base y antes de las relaciones)
from app.models.job import JobOpening, JobStatus
from app.models.candidate import Candidate, CandidateStatus
from app.models.evaluation import Evaluation
from app.models.rhtools import Document, DocumentTextExtraction, ResumeParse


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
