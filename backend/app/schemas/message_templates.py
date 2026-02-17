"""Schemas para Plantillas de Mensajes."""
import re
import html
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.schemas import sanitize_string, validate_no_html


class MessageChannel(str, Enum):
    """Canales de comunicación soportados."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"


# ============== TEMPLATE VARIABLE SCHEMAS ==============

class TemplateVariableBase(BaseModel):
    """Base para variables de plantilla."""
    name: str = Field(..., min_length=2, max_length=50, pattern=r'^[a-z_][a-z0-9_]*$')
    description: str = Field(..., min_length=5, max_length=255)
    example_value: Optional[str] = Field(None, max_length=255)
    category: str = Field(default="general", max_length=50)
    
    @field_validator('name')
    @classmethod
    def validate_variable_name(cls, v):
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        if not re.match(r'^[a-z_][a-z0-9_]*$', v):
            raise ValueError("El nombre debe usar snake_case: minúsculas y guiones bajos")
        return v
    
    @field_validator('description', 'example_value')
    @classmethod
    def sanitize_text(cls, v):
        if v:
            return sanitize_string(v, max_length=255)
        return v


class TemplateVariableCreate(TemplateVariableBase):
    """Crear variable de plantilla."""
    pass


class TemplateVariableUpdate(BaseModel):
    """Actualizar variable de plantilla."""
    description: Optional[str] = Field(None, max_length=255)
    example_value: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    
    @field_validator('description', 'example_value')
    @classmethod
    def sanitize_text(cls, v):
        if v:
            return sanitize_string(v, max_length=255)
        return v


class TemplateVariableResponse(TemplateVariableBase):
    """Respuesta de variable de plantilla."""
    variable_id: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_validator('variable_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


# ============== MESSAGE TEMPLATE SCHEMAS ==============

class MessageTemplateBase(BaseModel):
    """Base para plantillas de mensaje."""
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    channel: MessageChannel
    subject: Optional[str] = Field(None, max_length=255)
    body: str = Field(..., min_length=10, max_length=10000)
    variables: List[str] = Field(default=[], max_length=50)
    is_active: bool = True
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres")
        v = validate_no_html(v)
        return sanitize_string(v, max_length=100)
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v:
            v = validate_no_html(v)
            return sanitize_string(v, max_length=255)
        return v
    
    @field_validator('subject')
    @classmethod
    def validate_subject(cls, v, values):
        # Subject requerido para email
        channel = values.data.get('channel')
        if channel == MessageChannel.EMAIL and not v:
            raise ValueError("El asunto es requerido para plantillas de email")
        if v:
            v = validate_no_html(v)
            return sanitize_string(v, max_length=255)
        return v
    
    @field_validator('body')
    @classmethod
    def validate_body(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("El cuerpo debe tener al menos 10 caracteres")
        if len(v) > 10000:
            raise ValueError("El cuerpo no puede exceder 10000 caracteres")
        return v
    
    @field_validator('variables')
    @classmethod
    def validate_variables(cls, v):
        if v:
            if len(v) > 50:
                raise ValueError("Máximo 50 variables permitidas")
            # Validar formato de nombres de variables
            for var in v:
                if not re.match(r'^[a-z_][a-z0-9_]*$', var):
                    raise ValueError(f"Variable '{var}' inválida. Use snake_case.")
        return v


class MessageTemplateCreate(MessageTemplateBase):
    """Crear plantilla de mensaje."""
    pass


class MessageTemplateUpdate(BaseModel):
    """Actualizar plantilla de mensaje."""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    channel: Optional[MessageChannel] = None
    subject: Optional[str] = Field(None, max_length=255)
    body: Optional[str] = Field(None, max_length=10000)
    variables: Optional[List[str]] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v:
            if len(v.strip()) < 3:
                raise ValueError("El nombre debe tener al menos 3 caracteres")
            v = validate_no_html(v)
            return sanitize_string(v, max_length=100)
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v:
            v = validate_no_html(v)
            return sanitize_string(v, max_length=255)
        return v
    
    @field_validator('subject')
    @classmethod
    def validate_subject(cls, v):
        if v:
            v = validate_no_html(v)
            return sanitize_string(v, max_length=255)
        return v
    
    @field_validator('body')
    @classmethod
    def validate_body(cls, v):
        if v:
            if len(v.strip()) < 10:
                raise ValueError("El cuerpo debe tener al menos 10 caracteres")
            if len(v) > 10000:
                raise ValueError("El cuerpo no puede exceder 10000 caracteres")
        return v
    
    @field_validator('variables')
    @classmethod
    def validate_variables(cls, v):
        if v:
            if len(v) > 50:
                raise ValueError("Máximo 50 variables permitidas")
            for var in v:
                if not re.match(r'^[a-z_][a-z0-9_]*$', var):
                    raise ValueError(f"Variable '{var}' inválida. Use snake_case.")
        return v


class MessageTemplateResponse(MessageTemplateBase):
    """Respuesta de plantilla de mensaje."""
    template_id: str
    is_default: bool
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_validator('template_id', 'created_by', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class MessageTemplateListResponse(BaseModel):
    """Respuesta paginada de plantillas."""
    items: List[MessageTemplateResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


# ============== PREVIEW SCHEMAS ==============

class TemplatePreviewRequest(BaseModel):
    """Request para generar preview de plantilla."""
    variables: Dict[str, str] = Field(default={}, max_length=50)
    
    @field_validator('variables')
    @classmethod
    def validate_variables(cls, v):
        if v:
            if len(v) > 50:
                raise ValueError("Máximo 50 variables permitidas")
            # Sanitizar valores
            return {k: sanitize_string(str(val), max_length=1000) for k, val in v.items()}
        return v


class TemplatePreviewResponse(BaseModel):
    """Respuesta de preview de plantilla."""
    subject: Optional[str] = None
    body: str
    rendered_variables: Dict[str, str]
    missing_variables: List[str]
    extra_variables: List[str]


class RenderTemplateRequest(BaseModel):
    """Request para renderizar plantilla con variables."""
    template_id: str = Field(..., min_length=36, max_length=36)
    variables: Dict[str, str] = Field(default={}, max_length=50)
    
    @field_validator('variables')
    @classmethod
    def validate_variables(cls, v):
        if v:
            if len(v) > 50:
                raise ValueError("Máximo 50 variables permitidas")
            return {k: sanitize_string(str(val), max_length=1000) for k, val in v.items()}
        return v


class RenderTemplateResponse(BaseModel):
    """Respuesta de renderizado de plantilla."""
    subject: Optional[str] = None
    body: str
    channel: MessageChannel


# ============== AVAILABLE VARIABLES ==============

# Variables globales disponibles por defecto
DEFAULT_TEMPLATE_VARIABLES = [
    {"name": "candidate_name", "description": "Nombre completo del candidato", "example_value": "Juan Pérez", "category": "candidate"},
    {"name": "candidate_email", "description": "Correo electrónico del candidato", "example_value": "juan.perez@email.com", "category": "candidate"},
    {"name": "candidate_phone", "description": "Teléfono del candidato", "example_value": "+52 55 1234 5678", "category": "candidate"},
    {"name": "role_title", "description": "Título de la vacante", "example_value": "Desarrollador Senior Python", "category": "role"},
    {"name": "role_company", "description": "Nombre de la empresa", "example_value": "TechCorp", "category": "role"},
    {"name": "consultant_name", "description": "Nombre del consultor", "example_value": "María González", "category": "consultant"},
    {"name": "consultant_phone", "description": "Teléfono del consultor", "example_value": "+52 55 8765 4321", "category": "consultant"},
    {"name": "consultant_email", "description": "Email del consultor", "example_value": "maria@topmanagement.com", "category": "consultant"},
    {"name": "application_date", "description": "Fecha de aplicación", "example_value": "16 de febrero de 2025", "category": "system"},
    {"name": "current_date", "description": "Fecha actual", "example_value": "16 de febrero de 2025", "category": "system"},
]
