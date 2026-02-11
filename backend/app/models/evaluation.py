"""Modelos para Evaluaciones."""
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Evaluation(Base):
    """Evaluación de candidato con IA."""
    __tablename__ = "evaluations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    candidate = relationship("Candidate", back_populates="evaluations", lazy="selectin")
    
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
