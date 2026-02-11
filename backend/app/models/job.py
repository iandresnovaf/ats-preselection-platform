"""Modelos para Ofertas de Trabajo (Job Openings)."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class JobStatus(str, Enum):
    """Estados posibles de una oferta de trabajo."""
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"
    PAUSED = "paused"


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
    assigned_consultant = relationship("User", back_populates="assigned_jobs", lazy="selectin")
    
    # Zoho integration
    zoho_job_id = Column(String(100))
    
    # Estado
    is_active = Column(Boolean, default=True)
    status = Column(String(50), default=JobStatus.DRAFT.value)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    candidates = relationship("Candidate", back_populates="job_opening")
