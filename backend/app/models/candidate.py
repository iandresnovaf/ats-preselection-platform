"""Modelos para Candidatos."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Index
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
    
    # Índices compuestos para queries frecuentes
    __table_args__ = (
        Index('idx_candidates_job_status', 'job_opening_id', 'status'),
        Index('idx_candidates_created_at', 'created_at'),
        Index('idx_candidates_status_source', 'status', 'source'),
    )
    
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
    
    # External integrations
    zoho_candidate_id = Column(String(100), index=True)
    external_id = Column(String(100), index=True)  # ID genérico para cualquier ATS externo
    linkedin_url = Column(String(500))
    source = Column(String(50), default="manual")  # manual, zoho, odoo, linkedin, api
    
    # Anti-duplicados
    duplicate_of_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    is_duplicate = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    evaluations = relationship("Evaluation", back_populates="candidate")
    decisions = relationship("CandidateDecision", back_populates="candidate")
    # communications = relationship("Communication", back_populates="candidate")  # Usar nuevo sistema HHCandidate
    documents = relationship("Document", back_populates="candidate")
    match_results = relationship("MatchResult", back_populates="candidate", cascade="all, delete-orphan")
