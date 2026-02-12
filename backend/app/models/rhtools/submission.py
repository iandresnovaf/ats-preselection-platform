"""Modelos de Submissions para RHTools."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Boolean, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class SubmissionStatus(str, Enum):
    """Estados de una submission."""
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    WITHDRAWN = "withdrawn"
    HIRED = "hired"
    REJECTED = "rejected"


class Submission(Base):
    """
    Submission: Relación entre candidato, posición y cliente.
    Representa un candidato en proceso para una posición específica.
    """
    __tablename__ = "rhtools_submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relaciones clave
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    candidate = relationship("Candidate", foreign_keys=[candidate_id])
    
    client_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_clients.id"), nullable=False)
    client = relationship("Client", back_populates="submissions")
    
    job_opening_id = Column(UUID(as_uuid=True), ForeignKey("job_openings.id"), nullable=False)
    job_opening = relationship("JobOpening", foreign_keys=[job_opening_id])
    
    # Pipeline actual
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_pipeline_templates.id"))
    pipeline = relationship("PipelineTemplate")
    
    current_stage_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_pipeline_stages.id"))
    current_stage = relationship("PipelineStage", foreign_keys=[current_stage_id])
    
    # Información de la submission
    status = Column(String(20), default=SubmissionStatus.ACTIVE.value)
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    
    # Datos específicos de la submission
    salary_expectation = Column(Numeric(12, 2))
    salary_offered = Column(Numeric(12, 2))
    currency = Column(String(3), default="USD")
    
    # Fechas importantes
    applied_at = Column(DateTime, default=datetime.utcnow)
    first_contact_at = Column(DateTime)
    interview_scheduled_at = Column(DateTime)
    offer_sent_at = Column(DateTime)
    hired_at = Column(DateTime)
    rejected_at = Column(DateTime)
    
    # Razón de rechazo
    rejection_reason = Column(Text)
    rejection_stage_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_pipeline_stages.id"))
    
    # Datos adicionales
    source = Column(String(50), default="manual")  # manual, referral, linkedin, etc
    source_detail = Column(String(255))  # Detalle adicional de la fuente
    notes = Column(Text)
    custom_fields = Column(JSON)  # Campos personalizados
    
    # Owner/Consultor responsable
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    owner = relationship("User", foreign_keys=[owner_user_id])
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relations
    stage_history = relationship("SubmissionStageHistory", back_populates="submission", order_by="desc(SubmissionStageHistory.changed_at)")
    messages = relationship("Message", back_populates="submission")
    documents = relationship("Document", back_populates="submission")


class SubmissionStageHistory(Base):
    """Historial de cambios de etapa en una submission."""
    __tablename__ = "rhtools_submission_stage_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relación con submission
    submission_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_submissions.id"), nullable=False)
    submission = relationship("Submission", back_populates="stage_history")
    
    # Etapas
    from_stage_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_pipeline_stages.id"))
    from_stage = relationship("PipelineStage", foreign_keys=[from_stage_id])
    
    to_stage_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_pipeline_stages.id"))
    to_stage = relationship("PipelineStage", foreign_keys=[to_stage_id])
    
    # Información del cambio
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    changed_at = Column(DateTime, default=datetime.utcnow)
    
    # Notas sobre el cambio
    notes = Column(Text)
    reason = Column(String(255))  # Razón del cambio
    
    # Datos capturados en el cambio (campos requeridos)
    captured_data = Column(JSON)
    
    # Duración en la etapa anterior (calculado)
    duration_seconds = Column(Integer)  # Cuánto tiempo estuvo en la etapa anterior
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
