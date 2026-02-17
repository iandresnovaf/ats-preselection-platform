"""Modelo de Comunicaciones para WhatsApp Business API."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum, Index, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class CommunicationChannel(str, Enum):
    """Canales de comunicación soportados."""
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"


class CommunicationDirection(str, Enum):
    """Dirección del mensaje."""
    OUTBOUND = "outbound"  # Enviado por nosotros
    INBOUND = "inbound"    # Recibido del candidato


class CommunicationMessageType(str, Enum):
    """Tipo de mensaje."""
    INITIAL = "initial"      # Primer contacto
    FOLLOW_UP = "follow_up"  # Seguimiento
    REMINDER = "reminder"    # Recordatorio
    REPLY = "reply"          # Respuesta del candidato


class CommunicationStatus(str, Enum):
    """Estado del mensaje."""
    PENDING = "pending"      # En cola para enviar
    SENT = "sent"            # Enviado
    DELIVERED = "delivered"  # Entregado
    READ = "read"            # Leído
    FAILED = "failed"        # Falló
    REPLIED = "replied"      # Candidato respondió


class InterestStatus(str, Enum):
    """Estado de interés del candidato."""
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    UNKNOWN = "unknown"
    QUESTION = "question"  # Hizo una pregunta


class Communication(Base):
    """Modelo de comunicaciones con candidatos.
    
    Almacena todos los mensajes enviados y recibidos a través de
    WhatsApp Business API y otros canales.
    """
    __tablename__ = "communications"
    
    __table_args__ = (
        Index('idx_communications_application', 'application_id'),
        Index('idx_communications_candidate', 'candidate_id'),
        Index('idx_communications_status', 'status'),
        Index('idx_communications_whatsapp_id', 'whatsapp_message_id'),
        Index('idx_communications_created', 'created_at'),
        Index('idx_communications_phone', 'recipient_phone'),
    )
    
    # Identificador único
    communication_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Relaciones (pueden ser nulos dependiendo del contexto)
    application_id = Column(
        UUID(as_uuid=True),
        ForeignKey("hh_applications.application_id"),
        nullable=True
    )
    application = relationship("HHApplication", back_populates="communications")
    
    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("hh_candidates.candidate_id"),
        nullable=True
    )
    candidate = relationship("HHCandidate", back_populates="communications")
    
    # Canal y dirección
    channel = Column(
        SQLEnum(CommunicationChannel),
        nullable=False,
        default=CommunicationChannel.WHATSAPP
    )
    direction = Column(
        SQLEnum(CommunicationDirection),
        nullable=False,
        default=CommunicationDirection.OUTBOUND
    )
    message_type = Column(
        SQLEnum(CommunicationMessageType),
        nullable=False,
        default=CommunicationMessageType.INITIAL
    )
    
    # Contenido del mensaje
    template_id = Column(String(255), nullable=True)  # Nombre del template de WhatsApp
    content = Column(Text, nullable=False)  # Texto enviado o recibido
    variables = Column(JSONB, nullable=True)  # Variables usadas en el template
    
    # Información del destinatario
    recipient_phone = Column(String(25), nullable=True)
    recipient_name = Column(String(255), nullable=True)
    
    # Estado y tracking de WhatsApp
    whatsapp_message_id = Column(String(255), nullable=True, index=True)
    status = Column(
        SQLEnum(CommunicationStatus),
        nullable=False,
        default=CommunicationStatus.PENDING
    )
    
    # Timestamps de WhatsApp
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    # Información de error si falló
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Respuesta del candidato (para mensajes outbound)
    reply_to_id = Column(
        UUID(as_uuid=True),
        ForeignKey("communications.communication_id"),
        nullable=True
    )
    reply_whatsapp_id = Column(String(255), nullable=True)
    reply_content = Column(Text, nullable=True)
    reply_received_at = Column(DateTime, nullable=True)
    
    # Análisis de la respuesta
    interest_status = Column(
        SQLEnum(InterestStatus),
        nullable=True
    )
    response_metadata = Column(JSONB, nullable=True)
    
    # Metadata adicional
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    def __repr__(self):
        return (
            f"<Communication(id={self.communication_id}, "
            f"channel={self.channel}, "
            f"status={self.status}, "
            f"type={self.message_type})>"
        )
    
    def to_dict(self) -> dict:
        """Convierte el modelo a diccionario."""
        return {
            "communication_id": str(self.communication_id),
            "application_id": str(self.application_id) if self.application_id else None,
            "candidate_id": str(self.candidate_id) if self.candidate_id else None,
            "channel": self.channel.value if self.channel else None,
            "direction": self.direction.value if self.direction else None,
            "message_type": self.message_type.value if self.message_type else None,
            "template_id": self.template_id,
            "content": self.content,
            "recipient_phone": self.recipient_phone,
            "whatsapp_message_id": self.whatsapp_message_id,
            "status": self.status.value if self.status else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "reply_content": self.reply_content,
            "reply_received_at": self.reply_received_at.isoformat() if self.reply_received_at else None,
            "interest_status": self.interest_status.value if self.interest_status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
