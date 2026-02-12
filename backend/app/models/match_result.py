"""Modelo para almacenar resultados de matching IA entre candidatos y jobs."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Float, JSON, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class MatchRecommendation(str, Enum):
    """Recomendación del sistema de matching."""
    PROCEED = "PROCEED"      # Score > 75 - Candidato recomendado
    REVIEW = "REVIEW"        # Score 50-75 - Requiere revisión manual
    REJECT = "REJECT"        # Score < 50 - No cumple requisitos


class MatchResult(Base):
    """Resultado de matching entre un candidato y un job opening."""
    __tablename__ = "match_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relaciones
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True)
    candidate = relationship("Candidate", back_populates="match_results", lazy="selectin")
    
    job_opening_id = Column(UUID(as_uuid=True), ForeignKey("job_openings.id"), nullable=False, index=True)
    job_opening = relationship("JobOpening", back_populates="match_results", lazy="selectin")
    
    # Score general 0-100
    score = Column(Float, nullable=False, index=True)
    
    # Detalles del match (estructurado)
    match_details = Column(JSON, default=dict)  # {
    #     "skills_match": {
    #         "required_skills_percentage": 85.0,
    #         "matched_skills": ["Python", "React"],
    #         "missing_skills": ["AWS"],
    #         "extra_skills": ["Docker"]
    #     },
    #     "experience_match": {
    #         "years_found": 5,
    #         "years_required": 3,
    #         "match_percentage": 100.0
    #     },
    #     "education_match": {
    #         "match_percentage": 100.0,
    #         "details": "Bachelor in Computer Science found"
    #     }
    # }
    
    # Recomendación del sistema
    recommendation = Column(String(20), nullable=False, index=True)  # PROCEED, REVIEW, REJECT
    
    # Razonamiento detallado de la IA
    reasoning = Column(Text)  # Explicación textual del análisis
    
    # Fortalezas identificadas
    strengths = Column(JSON, default=list)  # ["Strong Python skills", "5 years experience"]
    
    # Gaps identificados
    gaps = Column(JSON, default=list)  # ["No AWS experience", "Missing certification"]
    
    # Red flags si existen
    red_flags = Column(JSON, default=list)  # ["Job hopping", "Employment gap"]
    
    # Metadatos del análisis
    analysis_duration_ms = Column(Integer)  # Tiempo que tomó el análisis
    llm_provider = Column(String(50))  # openai, anthropic, etc.
    llm_model = Column(String(100))  # gpt-4o-mini, etc.
    prompt_version = Column(String(20))  # v1.0, etc.
    
    # Auditoría
    analyzed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    analyzed_by_user = relationship("User", lazy="selectin")
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    
    # Cache control
    is_cached = Column(String(1), default="N")  # Y/N - Si es resultado cacheado
    cache_expires_at = Column(DateTime, nullable=True)  # Cuándo expira el cache
    
    # Campos hash para invalidación de cache
    cv_version_hash = Column(String(64))  # Hash del contenido del CV
    job_version_hash = Column(String(64))  # Hash de los requisitos del job
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MatchingAuditLog(Base):
    """Log de auditoría para operaciones de matching."""
    __tablename__ = "matching_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Acción realizada
    action = Column(String(50), nullable=False)  # ANALYZE, BATCH_ANALYZE, VIEW, EXPORT
    
    # Entidades involucradas
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=True, index=True)
    job_opening_id = Column(UUID(as_uuid=True), ForeignKey("job_openings.id"), nullable=True, index=True)
    match_result_id = Column(UUID(as_uuid=True), ForeignKey("match_results.id"), nullable=True)
    
    # Usuario que realizó la acción
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    user = relationship("User", lazy="selectin")
    
    # Detalles de la operación
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    request_method = Column(String(10))
    request_path = Column(String(500))
    
    # Resultado
    success = Column(String(1), default="Y")  # Y/N
    error_message = Column(Text)
    processing_time_ms = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
