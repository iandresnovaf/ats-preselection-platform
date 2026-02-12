"""Modelos extendidos de Candidatos para RHTools."""
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class CandidateOfflimits(Base):
    """
    Registro de candidatos en offlimits para un cliente.
    Un candidato no puede ser contactado por otros clientes si está en offlimits.
    """
    __tablename__ = "rhtools_candidate_offlimits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relaciones
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    candidate = relationship("Candidate")
    
    client_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_clients.id"), nullable=False)
    client = relationship("Client", back_populates="offlimits")
    
    # Detalles del offlimits
    reason = Column(Text)  # Razón del offlimits
    notes = Column(Text)
    
    # Período de offlimits
    starts_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Null = indefinido
    
    # Estado
    is_active = Column(Boolean, default=True)
    auto_expire = Column(Boolean, default=True)  # Expirar automáticamente
    
    # Creado por
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expired_at = Column(DateTime)  # Cuando se marcó como expirado
    
    def is_expired(self) -> bool:
        """Verificar si el offlimits ha expirado."""
        if not self.is_active:
            return True
        if self.expires_at and self.expires_at < datetime.utcnow():
            return True
        return False
    
    def days_until_expiry(self) -> int:
        """Días hasta la expiración."""
        if not self.expires_at:
            return -1  # No expira
        if self.is_expired():
            return 0
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)


class ResumeParse(Base):
    """Parseo de CV con datos estructurados."""
    __tablename__ = "rhtools_resume_parses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relación con candidato
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    candidate = relationship("Candidate")
    
    # Relación con documento (si existe)
    document_id = Column(UUID(as_uuid=True), ForeignKey("rhtools_documents.id"))
    
    # Estado
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    
    # Datos extraídos
    parsed_data = Column(JSON)  # Datos estructurados completos
    
    # Campos específicos extraídos
    full_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    location = Column(String(255))
    
    # Educación
    education = Column(JSON)  # Lista de instituciones, títulos, fechas
    highest_education_level = Column(String(50))
    
    # Experiencia
    experience_years = Column(Integer)  # Años totales de experiencia
    work_experience = Column(JSON)  # Lista de experiencias laborales
    current_title = Column(String(255))
    current_company = Column(String(255))
    
    # Skills
    skills = Column(JSON)  # Lista de habilidades
    skills_raw = Column(Text)  # Texto crudo de skills
    
    # Idiomas
    languages = Column(JSON)
    
    # Resumen
    summary = Column(Text)
    
    # Motor de parseo
    parser_engine = Column(String(50))  # openai, azure, custom, etc
    parser_version = Column(String(20))
    
    # Error
    error_message = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime)


class CandidateProfileVersion(Base):
    """Versionado del perfil de candidato para auditoría."""
    __tablename__ = "rhtools_candidate_profile_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relación con candidato
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    
    # Número de versión
    version_number = Column(Integer, nullable=False)
    
    # Tipo de cambio
    change_type = Column(String(50))  # create, update, merge, etc
    change_reason = Column(Text)
    
    # Snapshot de datos
    snapshot_data = Column(JSON)  # Datos completos del candidato en este momento
    
    # Datos específicos
    full_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    raw_data = Column(JSON)
    extracted_skills = Column(JSON)
    extracted_experience = Column(JSON)
    extracted_education = Column(JSON)
    
    # Quién hizo el cambio
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Índice único para versión
    __table_args__ = (
        # Cada candidato tiene versiones numeradas secuencialmente
        # No usamos UniqueConstraint aquí porque SQLAlchemy lo maneja diferente
        # Se creará con una migración posterior si es necesario
    )
