"""Modelo de Clientes para RHTools."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class ClientStatus(str, Enum):
    """Estados posibles de un cliente."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class Client(Base):
    """Cliente (empresa) en RHTools."""
    __tablename__ = "rhtools_clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relación con cuenta/tenant
    account_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    account = relationship("User", foreign_keys=[account_id])
    
    # Información básica
    name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255))
    tax_id = Column(String(50))  # NIT/RUT/CUIT/etc
    
    # Industria y sector
    industry = Column(String(100), index=True)
    sector = Column(String(100))
    company_size = Column(String(50))  # startup, smb, enterprise, etc
    
    # Contacto y web
    website = Column(String(500))
    email = Column(String(255))
    phone = Column(String(50))
    
    # Dirección
    address = Column(Text)
    city = Column(String(100))
    country = Column(String(100))
    
    # Owner/Consultor responsable
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    owner = relationship("User", foreign_keys=[owner_user_id])
    
    # Estado
    status = Column(String(20), default=ClientStatus.ACTIVE.value, index=True)
    is_deleted = Column(Boolean, default=False)
    
    # Configuración específica del cliente
    settings = Column(Text)  # JSON con configuraciones personalizadas
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)
    
    # Relations
    pipelines = relationship("PipelineTemplate", back_populates="client")
    submissions = relationship("Submission", back_populates="client")
    documents = relationship("Document", back_populates="client")
    messages = relationship("Message", back_populates="client")
    offlimits = relationship("CandidateOfflimits", back_populates="client")
    
    def soft_delete(self):
        """Soft delete del cliente."""
        self.is_deleted = True
        self.status = ClientStatus.INACTIVE.value
        self.deleted_at = datetime.utcnow()
