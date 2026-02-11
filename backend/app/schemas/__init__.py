"""Schemas Pydantic."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, EmailStr, field_validator


# ============== CONFIGURATION SCHEMAS ==============

class ConfigCategory(str, Enum):
    WHATSAPP = "whatsapp"
    ZOHO = "zoho"
    LLM = "llm"
    EMAIL = "email"
    GENERAL = "general"


class ConfigurationBase(BaseModel):
    """Base para configuraciones."""
    category: ConfigCategory
    key: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_json: bool = False


class ConfigurationCreate(ConfigurationBase):
    """Crear configuración."""
    value: str = Field(..., min_length=1)
    is_encrypted: bool = True


class ConfigurationUpdate(BaseModel):
    """Actualizar configuración."""
    value: Optional[str] = None
    description: Optional[str] = None
    is_encrypted: Optional[bool] = None


class ConfigurationResponse(ConfigurationBase):
    """Respuesta de configuración (valor descifrado o enmascarado)."""
    id: str
    value: Optional[str] = None
    value_masked: Optional[str] = None
    is_encrypted: bool
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class ConfigurationValue(BaseModel):
    """Valor simple de configuración."""
    value: str


# ============== CONFIG GROUP SCHEMAS ==============

class WhatsAppConfig(BaseModel):
    """Configuración de WhatsApp Business API."""
    access_token: str = Field(..., description="Token de acceso de Meta")
    phone_number_id: str = Field(..., description="ID del número de teléfono")
    verify_token: str = Field(..., description="Token de verificación de webhook")
    app_secret: Optional[str] = Field(None, description="App Secret para verificación")
    business_account_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "EAAB...",
                "phone_number_id": "123456789",
                "verify_token": "webhook_verify_token",
                "app_secret": "app_secret_optional",
            }
        }


class ATSProvider(str, Enum):
    """Proveedores de ATS soportados."""
    ZOHO = "zoho"
    ODOO = "odoo"


class ZohoConfig(BaseModel):
    """Configuración de Zoho Recruit API."""
    client_id: str
    client_secret: str
    refresh_token: str
    redirect_uri: str = "http://localhost:8000/api/v1/zoho/callback"
    
    # Mapeo de campos
    job_id_field: str = "Job_Opening_ID"
    candidate_id_field: str = "Candidate_ID"
    stage_field: str = "Stage"
    
    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "1000.xxxxx",
                "client_secret": "client_secret_here",
                "refresh_token": "refresh_token_here",
                "redirect_uri": "http://localhost:8000/api/v1/zoho/callback",
            }
        }


class OdooConfig(BaseModel):
    """Configuración de Odoo API."""
    url: str = Field(..., description="URL de la instancia Odoo (ej: https://miempresa.odoo.com)")
    database: str = Field(..., description="Nombre de la base de datos")
    username: str = Field(..., description="Email del usuario")
    api_key: str = Field(..., description="API Key o Password")
    
    # Mapeo de campos (Odoo usa modelos diferentes)
    job_model: str = "hr.job"  # Modelo de puestos de trabajo
    applicant_model: str = "hr.applicant"  # Modelo de candidatos
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://miempresa.odoo.com",
                "database": "miempresa_prod",
                "username": "admin@miempresa.com",
                "api_key": "api_key_o_password",
            }
        }


class LLMConfig(BaseModel):
    """Configuración de LLM."""
    provider: str = Field(default="openai", description="openai, anthropic, etc")
    api_key: str
    model: str = Field(default="gpt-4o-mini")
    max_tokens: int = Field(default=2000)
    temperature: float = Field(default=0.0, ge=0, le=2)
    
    # Versionado de prompts
    prompt_version: str = "v1.0"
    
    class Config:
        json_schema_extra = {
            "example": {
                "provider": "openai",
                "api_key": "sk-...",
                "model": "gpt-4o-mini",
                "max_tokens": 2000,
                "temperature": 0.0,
            }
        }


class EmailConfig(BaseModel):
    """Configuración de Email (SMTP)."""
    provider: str = Field(default="smtp", description="smtp, sendgrid, mailgun")
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    use_tls: bool = True
    default_from: EmailStr
    default_from_name: str = "Top Management"
    
    class Config:
        json_schema_extra = {
            "example": {
                "provider": "smtp",
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_user": "noreply@example.com",
                "smtp_password": "password",
                "default_from": "noreply@example.com",
                "default_from_name": "Top Management",
            }
        }


class SystemStatus(BaseModel):
    """Estado del sistema e integraciones."""
    database: bool
    redis: bool
    whatsapp: Optional[bool] = None
    zoho: Optional[bool] = None
    llm: Optional[bool] = None
    email: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "database": True,
                "redis": True,
                "whatsapp": None,
                "zoho": None,
                "llm": None,
                "email": None,
            }
        }


# ============== USER SCHEMAS ==============

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role: str = "consultant"


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


class UserResponse(UserBase):
    id: str
    role: str
    status: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v

    @field_validator('status', 'role', mode='before')
    @classmethod
    def convert_enum_to_str(cls, v):
        if v is not None and hasattr(v, 'value'):
            return v.value
        return v


# ============== AUTH SCHEMAS ==============

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class EmailChange(BaseModel):
    new_email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# ============== JOB OPENING SCHEMAS ==============

class JobOpeningBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str
    department: Optional[str] = None
    location: Optional[str] = None
    seniority: Optional[str] = None
    sector: Optional[str] = None


class JobOpeningCreate(JobOpeningBase):
    assigned_consultant_id: Optional[str] = None


class JobOpeningUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    seniority: Optional[str] = None
    sector: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    assigned_consultant_id: Optional[str] = None


class JobOpeningResponse(JobOpeningBase):
    id: str
    assigned_consultant_id: Optional[str] = None
    zoho_job_id: Optional[str] = None
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'assigned_consultant_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


# ============== CANDIDATE SCHEMAS ==============

class CandidateBase(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None


class CandidateCreate(BaseModel):
    job_opening_id: str
    raw_data: Dict[str, Any]
    source: str = "manual"


class CandidateUpdate(BaseModel):
    status: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None


class CandidateResponse(CandidateBase):
    id: str
    job_opening_id: str
    status: str
    zoho_candidate_id: Optional[str] = None
    is_duplicate: bool
    duplicate_of_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    source: str
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'job_opening_id', 'duplicate_of_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


# ============== EVALUATION SCHEMAS ==============

class EvaluationCreate(BaseModel):
    """Crear evaluación (usado internamente)."""
    candidate_id: str
    score: float = Field(..., ge=0, le=100)
    decision: str
    strengths: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
    red_flags: Optional[List[str]] = None
    evidence: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    prompt_version: Optional[str] = None


class EvaluationResponse(BaseModel):
    id: str
    candidate_id: str
    score: float
    decision: str
    strengths: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
    red_flags: Optional[List[str]] = None
    evidence: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    prompt_version: Optional[str] = None
    created_at: datetime
    evaluation_time_ms: Optional[int] = None
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'candidate_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class CandidateWithEvaluation(CandidateResponse):
    evaluations: List[EvaluationResponse] = []
    latest_score: Optional[float] = None
    latest_decision: Optional[str] = None


# ============== COMMUNICATION SCHEMAS ==============

class CommunicationTemplate(BaseModel):
    name: str
    type: str  # whatsapp, email
    subject: Optional[str] = None
    body: str
    variables: List[str] = []


class SendCommunicationRequest(BaseModel):
    candidate_id: str
    template_name: str
    variables: Dict[str, str] = {}


# ============== JOB PAGINATION SCHEMAS ==============

class JobListResponse(BaseModel):
    """Respuesta paginada de ofertas."""
    items: List[JobOpeningResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


class CandidateListResponse(BaseModel):
    """Respuesta paginada de candidatos."""
    items: List[CandidateResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


class EvaluationListResponse(BaseModel):
    """Respuesta paginada de evaluaciones."""
    items: List[EvaluationResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


# ============== REQUEST SCHEMAS ==============

class ChangeStatusRequest(BaseModel):
    """Request para cambiar estado."""
    status: str


class EvaluateRequest(BaseModel):
    """Request para evaluar candidato."""
    force: bool = False  # Forzar re-evaluación


class CloseJobRequest(BaseModel):
    """Request para cerrar oferta."""
    reason: Optional[str] = None


# ============== RESPONSE SCHEMAS ==============

class PaginatedResponse(BaseModel):
    """Respuesta paginada genérica."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


class MessageResponse(BaseModel):
    """Respuesta simple con mensaje."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Respuesta de error."""
    detail: str
    error_code: Optional[str] = None
    field_errors: Optional[Dict[str, str]] = None
