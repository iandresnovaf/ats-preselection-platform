"""Modelos para Ofertas de Trabajo (Job Openings)."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Integer, JSON
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


class EmploymentType(str, Enum):
    """Tipos de empleo."""
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"


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
    
    # Requisitos estructurados para matching con IA
    requirements = Column(JSON, default=dict)  # {
    #     "required_skills": ["Python", "React", "AWS"],
    #     "preferred_skills": ["Docker", "Kubernetes"],
    #     "min_years_experience": 3,
    #     "education_level": "bachelor",
    #     "education_fields": ["Computer Science", "Engineering"],
    #     "languages": [{"language": "English", "level": "fluent"}],
    #     "certifications": ["AWS Solutions Architect"]
    # }
    
    # Rango salarial (opcional)
    salary_range_min = Column(Integer, nullable=True)
    salary_range_max = Column(Integer, nullable=True)
    
    # Tipo de empleo
    employment_type = Column(String(50), default=EmploymentType.FULL_TIME.value)
    
    # Documento PDF del Job Description
    job_description_file_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_documents.id"), nullable=True)
    job_description_document = relationship("Document", foreign_keys=[job_description_file_id], lazy="selectin")
    
    # Relación con consultor
    assigned_consultant_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assigned_consultant = relationship("User", back_populates="assigned_jobs", lazy="selectin")
    
    # External integrations
    zoho_job_id = Column(String(100), index=True)
    external_id = Column(String(100), index=True)  # ID genérico para cualquier ATS externo
    source = Column(String(50), default="manual")  # manual, zoho, odoo, api
    
    # Estado
    is_active = Column(Boolean, default=True)
    status = Column(String(50), default=JobStatus.DRAFT.value)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    candidates = relationship("Candidate", back_populates="job_opening")
    match_results = relationship("MatchResult", back_populates="job_opening", cascade="all, delete-orphan")
