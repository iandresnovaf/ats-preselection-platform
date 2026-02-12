"""Modelos de Pipeline para RHTools."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class PipelineTemplate(Base):
    """Template de pipeline para procesos de selección."""
    __tablename__ = "rhtools_pipeline_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relación con cliente
    client_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_clients.id"), nullable=False)
    client = relationship("Client", back_populates="pipelines")
    
    # Información básica
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Tipo de pipeline
    pipeline_type = Column(String(50), default="recruitment")  # recruitment, internal, etc
    
    # Orden y estado
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    order_index = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relations
    stages = relationship("PipelineStage", back_populates="pipeline", order_by="PipelineStage.order_index")


class PipelineStage(Base):
    """Etapa/stage dentro de un pipeline."""
    __tablename__ = "rhtools_pipeline_stages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relación con pipeline
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_pipeline_templates.id"), nullable=False)
    pipeline = relationship("PipelineTemplate", back_populates="stages")
    
    # Información básica
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Orden dentro del pipeline
    order_index = Column(Integer, nullable=False, default=0)
    
    # Configuración
    color = Column(String(7), default="#3B82F6")  # Hex color
    is_required = Column(Boolean, default=False)  # Etapa obligatoria
    is_final = Column(Boolean, default=False)  # Etapa final (hired/rejected)
    
    # SLAs
    sla_hours = Column(Integer)  # SLA en horas para esta etapa
    auto_advance = Column(Boolean, default=False)  # Auto-avanzar si cumple condiciones
    
    # Estado
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    required_fields = relationship("StageRequiredField", back_populates="stage", cascade="all, delete-orphan")
    message_rules = relationship("StageMessageRule", back_populates="stage")
    
    # Helper para validar transición
    def can_transition_to(self, target_stage_id: str) -> bool:
        """Verificar si se puede transicionar a otra etapa."""
        # Por defecto, solo se puede avanzar o retroceder una etapa
        # o saltar a cualquier etapa si es admin
        return True  # Implementar lógica más compleja si es necesario


class StageRequiredField(Base):
    """Campos requeridos para una etapa específica."""
    __tablename__ = "rhtools_stage_required_fields"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relación con stage
    stage_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_pipeline_stages.id"), nullable=False)
    stage = relationship("PipelineStage", back_populates="required_fields")
    
    # Campo requerido
    field_name = Column(String(100), nullable=False)  # Ej: "salary_expectation", "interview_notes"
    field_type = Column(String(50), default="text")  # text, number, date, file, etc
    field_label = Column(String(255))  # Label para mostrar al usuario
    
    # Validación
    is_required = Column(Boolean, default=True)
    validation_rules = Column(JSON)  # Reglas de validación JSON
    
    # Configuración
    help_text = Column(Text)
    default_value = Column(String(500))
    
    # Orden
    order_index = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
