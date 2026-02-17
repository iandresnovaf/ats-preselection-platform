"""Modelo de Plantillas de Mensajes."""
from datetime import datetime
from enum import Enum
from typing import Optional, List
import uuid

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, 
    Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class MessageChannel(str, Enum):
    """Canales de comunicación soportados."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"


class MessageTemplate(Base):
    """Plantilla de mensaje para comunicaciones con candidatos."""
    __tablename__ = "message_templates"
    
    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, index=True)  # "Contacto Inicial"
    description = Column(String(255))  # "Primer contacto con candidato"
    channel = Column(SQLEnum(MessageChannel), nullable=False, index=True)
    subject = Column(String(255))  # solo para email
    body = Column(Text, nullable=False)  # Contenido con variables {nombre}
    variables = Column(JSONB, default=list)  # ["nombre", "vacante", "empresa"]
    is_active = Column(Boolean, default=True, index=True)
    is_default = Column(Boolean, default=False)  # Plantillas del sistema
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    creator = relationship("User", foreign_keys=[created_by])
    
    __table_args__ = (
        UniqueConstraint('name', 'channel', name='uix_template_name_channel'),
    )
    
    def __repr__(self):
        return f"<MessageTemplate {self.name} ({self.channel})>"


class TemplateVariable(Base):
    """Variables disponibles globalmente para plantillas."""
    __tablename__ = "template_variables"
    
    variable_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True, index=True)  # candidate_name
    description = Column(String(255), nullable=False)  # "Nombre del candidato"
    example_value = Column(String(255))  # "Juan Pérez"
    category = Column(String(50), default="general")  # candidate, role, consultant, system
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TemplateVariable {self.name}>"
