"""Modelos de Documentos para RHTools."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class DocumentType(str, Enum):
    """Tipos de documentos."""
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    PORTFOLIO = "portfolio"
    CONTRACT = "contract"
    OFFER_LETTER = "offer_letter"
    INTERVIEW_NOTES = "interview_notes"
    EVALUATION = "evaluation"
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Estados de un documento."""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"


class Document(Base):
    """Documento asociado a una submission o candidato."""
    __tablename__ = "rhtools_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relaciones
    submission_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_submissions.id"), nullable=True)
    submission = relationship("Submission", back_populates="documents")
    
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=True)
    candidate = relationship("Candidate", foreign_keys=[candidate_id])
    
    client_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_clients.id"), nullable=True)
    client = relationship("Client", back_populates="documents")
    
    # Información del archivo
    original_filename = Column(String(500), nullable=False)
    storage_filename = Column(String(500), nullable=False)  # Nombre único en storage
    file_path = Column(String(1000), nullable=False)  # Ruta completa en storage
    file_size = Column(Integer)  # Tamaño en bytes
    mime_type = Column(String(100))
    checksum = Column(String(64))  # SHA-256 del archivo
    
    # Tipo de documento
    document_type = Column(String(50), default=DocumentType.OTHER.value)
    document_category = Column(String(50))  # Para categorización adicional
    
    # Estado de procesamiento
    status = Column(String(20), default=DocumentStatus.PENDING.value)
    
    # Visibilidad
    is_private = Column(Boolean, default=False)  # Solo visible para admins
    is_shared_with_candidate = Column(Boolean, default=False)
    
    # Metadatos extraídos
    extracted_metadata = Column(JSON)  # Metadatos del archivo (páginas, autor, etc)
    extracted_text = Column(Text)  # Texto extraído (si aplica)
    
    # Notas
    description = Column(Text)
    tags = Column(JSON)  # Lista de tags
    
    # Subido por
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Expiración (para documentos temporales)
    expires_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    text_extraction = relationship("DocumentTextExtraction", back_populates="document", uselist=False)


class DocumentTextExtraction(Base):
    """Extracción de texto de documentos (para búsquedas)."""
    __tablename__ = "rhtools_document_text_extractions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relación con documento
    document_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_documents.id"), nullable=False)
    document = relationship("Document", back_populates="text_extraction")
    
    # Estado
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    
    # Resultado
    extracted_text = Column(Text)  # Texto completo extraído
    extracted_text_clean = Column(Text)  # Texto limpio para búsqueda
    extracted_metadata = Column(JSON)  # Metadatos extraídos (título, autor, fechas, etc)
    
    # Para CVs: datos estructurados extraídos
    parsed_data = Column(JSON)  # Datos estructurados (skills, experiencia, etc)
    
    # Error
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Motor de extracción usado
    extraction_engine = Column(String(50))  # tika, pdfplumber, custom, etc
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime)
