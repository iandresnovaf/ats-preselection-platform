"""Modelos de Comunicación para RHTools."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class MessageType(str, Enum):
    """Tipos de mensajes."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    INTERNAL = "internal"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    """Estados de un mensaje."""
    DRAFT = "draft"
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageDirection(str, Enum):
    """Dirección del mensaje."""
    OUTBOUND = "outbound"  # Sistema -> Candidato
    INBOUND = "inbound"    # Candidato -> Sistema


class RHtoolsMessageTemplate(Base):
    """Template de mensajes para comunicaciones (RHtools legacy)."""
    __tablename__ = "rhtools_message_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Información básica
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Tipo de mensaje
    message_type = Column(String(20), default=MessageType.EMAIL.value)  # email, whatsapp, sms
    
    # Contenido
    subject = Column(String(500))  # Para email
    body_text = Column(Text, nullable=False)  # Versión texto plano
    body_html = Column(Text)  # Versión HTML (para email)
    
    # Variables disponibles
    variables = Column(JSON)  # Lista de variables: ["candidate_name", "job_title", etc]
    
    # Configuración
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # No se puede eliminar
    category = Column(String(50))  # invitation, rejection, offer, etc
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relations
    stage_rules = relationship("StageMessageRule", back_populates="template")


class StageMessageRule(Base):
    """Reglas para enviar mensajes automáticamente al cambiar de etapa."""
    __tablename__ = "rhtools_stage_message_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relación con stage
    stage_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_pipeline_stages.id"), nullable=False)
    stage = relationship("PipelineStage", back_populates="message_rules")
    
    # Template a usar
    template_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_message_templates.id"), nullable=False)
    template = relationship("RHtoolsMessageTemplate", back_populates="stage_rules")
    
    # Condiciones
    trigger_event = Column(String(50), default="stage_enter")  # stage_enter, stage_exit, etc
    delay_minutes = Column(Integer, default=0)  # Retraso antes de enviar
    
    # Condiciones adicionales
    conditions = Column(JSON)  # Condiciones JSON para activar
    
    # Configuración
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    """Mensaje enviado/recibido."""
    __tablename__ = "rhtools_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relaciones
    submission_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_submissions.id"), nullable=True)
    submission = relationship("Submission", back_populates="messages")
    
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=True)
    candidate = relationship("Candidate", foreign_keys=[candidate_id])
    
    client_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_clients.id"), nullable=True)
    client = relationship("Client", back_populates="messages")
    
    # Template usado (si aplica)
    template_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_message_templates.id"))
    
    # Tipo y dirección
    message_type = Column(String(20), default=MessageType.EMAIL.value)
    direction = Column(String(20), default=MessageDirection.OUTBOUND.value)
    
    # Contenido
    subject = Column(String(500))
    body_text = Column(Text)
    body_html = Column(Text)
    
    # Datos procesados (variables reemplazadas)
    processed_body = Column(Text)
    
    # Destinatario/remitente
    from_address = Column(String(255))
    to_address = Column(String(255))
    cc_addresses = Column(JSON)
    bcc_addresses = Column(JSON)
    
    # Estado
    status = Column(String(20), default=MessageStatus.PENDING.value)
    
    # Tracking
    external_message_id = Column(String(255))  # ID del proveedor (SendGrid, Twilio, etc)
    thread_id = Column(String(255))  # ID de conversación
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_messages.id"))
    
    # Timestamps
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)
    scheduled_at = Column(DateTime)  # Para mensajes programados
    
    # Error
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Enviado por
    sent_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Metadata adicional
    extra_data = Column(JSON)  # Datos adicionales del mensaje (renamed from metadata - reserved word)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
