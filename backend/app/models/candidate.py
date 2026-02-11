"""Modelos para Candidatos."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class CandidateStatus(str, Enum):
    """Estados posibles de un candidato."""
    NEW = "new"
    SCREENING = "screening"
    INTERVIEW = "interview"
    EVALUATION = "evaluation"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"


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
    job_opening = relationship("JobOpening", back_populates="candidates", lazy="selectin")
    
    # Estado
    status = Column(String(50), default=CandidateStatus.NEW.value)
    
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
