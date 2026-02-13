"""Schemas Pydantic con validaciones de seguridad."""
import html
import re
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator


# ============== VALIDADORES DE SEGURIDAD ==============

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitiza un string para prevenir XSS."""
    if not value:
        return value
    
    # Escapar HTML
    value = html.escape(value)
    
    # Limitar longitud
    if len(value) > max_length:
        value = value[:max_length]
    
    return value


def validate_uuid(value: str) -> str:
    """Valida que un string sea un UUID válido."""
    if not value:
        return value
    try:
        uuid.UUID(str(value))
        return str(value)
    except ValueError:
        raise ValueError("Formato UUID inválido")


def validate_phone(value: str) -> str:
    """Valida formato de teléfono internacional."""
    if not value:
        return value
    
    # Permitir solo dígitos, +, -, espacios y paréntesis
    pattern = r'^[\d\s\-\+\(\)\.]+$'
    if not re.match(pattern, value):
        raise ValueError("Formato de teléfono inválido")
    
    # Limitar longitud (E.164 max 15 dígitos + formato)
    if len(value) > 25:
        raise ValueError("Número de teléfono demasiado largo")
    
    return value


def validate_no_html(value: str) -> str:
    """Verifica que no haya tags HTML."""
    if not value:
        return value
    
    # Detectar tags HTML
    html_pattern = re.compile(r'<[^>]+>')
    if html_pattern.search(value):
        raise ValueError("El campo no debe contener HTML")
    
    return value


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
    key: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_\-]+$')
    description: Optional[str] = Field(None, max_length=500)
    is_json: bool = False
    
    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        if not v:
            raise ValueError("La clave no puede estar vacía")
        if len(v) > 100:
            raise ValueError("La clave no puede exceder 100 caracteres")
        return v
    
    @field_validator('description')
    @classmethod
    def sanitize_description(cls, v):
        if v:
            return sanitize_string(v, max_length=500)
        return v


class ConfigurationCreate(ConfigurationBase):
    """Crear configuración."""
    value: str = Field(..., min_length=1, max_length=10000)
    is_encrypted: bool = True
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v):
        if not v:
            raise ValueError("El valor no puede estar vacío")
        if len(v) > 10000:
            raise ValueError("El valor no puede exceder 10000 caracteres")
        return v


class ConfigurationUpdate(BaseModel):
    """Actualizar configuración."""
    value: Optional[str] = Field(None, max_length=10000)
    description: Optional[str] = Field(None, max_length=500)
    is_encrypted: Optional[bool] = None
    
    @field_validator('description')
    @classmethod
    def sanitize_description(cls, v):
        if v:
            return sanitize_string(v, max_length=500)
        return v
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v):
        if v and len(v) > 10000:
            raise ValueError("El valor no puede exceder 10000 caracteres")
        return v


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
    value: str = Field(..., max_length=10000)


# ============== CONFIG GROUP SCHEMAS ==============

class WhatsAppConfig(BaseModel):
    """Configuración de WhatsApp Business API."""
    access_token: str = Field(..., description="Token de acceso de Meta", max_length=500)
    phone_number_id: str = Field(..., description="ID del número de teléfono", max_length=50)
    verify_token: str = Field(..., description="Token de verificación de webhook", max_length=100)
    app_secret: Optional[str] = Field(None, description="App Secret para verificación", max_length=500)
    business_account_id: Optional[str] = Field(None, max_length=50)
    
    @field_validator('access_token', 'verify_token', 'app_secret')
    @classmethod
    def validate_tokens(cls, v):
        if v and len(v) > 1000:
            raise ValueError("Token demasiado largo")
        return v


class ATSProvider(str, Enum):
    """Proveedores de ATS soportados."""
    ZOHO = "zoho"
    ODOO = "odoo"
    RHTOOLS = "rhtools"


class ZohoConfig(BaseModel):
    """Configuración de Zoho Recruit API."""
    client_id: str = Field(..., max_length=200)
    client_secret: str = Field(..., max_length=500)
    refresh_token: str = Field(..., max_length=500)
    redirect_uri: str = Field(default="http://localhost:8000/api/v1/zoho/callback", max_length=500)
    
    # Mapeo de campos
    job_id_field: str = Field(default="Job_Opening_ID", max_length=100)
    candidate_id_field: str = Field(default="Candidate_ID", max_length=100)
    stage_field: str = Field(default="Stage", max_length=100)
    
    @field_validator('redirect_uri')
    @classmethod
    def validate_redirect_uri(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("Redirect URI debe ser una URL válida")
        return v


class OdooConfig(BaseModel):
    """Configuración de Odoo API."""
    url: str = Field(..., description="URL de la instancia Odoo", max_length=500)
    database: str = Field(..., description="Nombre de la base de datos", max_length=100)
    username: EmailStr = Field(..., description="Email del usuario")
    api_key: str = Field(..., description="API Key o Password", max_length=500)
    
    # Mapeo de campos (Odoo usa modelos diferentes)
    job_model: str = Field(default="hr.job", max_length=100)
    applicant_model: str = Field(default="hr.applicant", max_length=100)
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL debe comenzar con http:// o https://")
        if len(v) > 500:
            raise ValueError("URL demasiado larga")
        return v


class RHToolsConfig(BaseModel):
    """Configuración de RHTools ATS ( próximo ATS propio)."""
    api_url: str = Field(..., description="URL de la API de RHTools", max_length=500)
    api_key: str = Field(..., description="API Key de RHTools", max_length=500)
    client_id: str = Field(..., description="ID de cliente", max_length=100)
    
    # Webhook para recibir actualizaciones
    webhook_secret: Optional[str] = Field(None, description="Secret para verificar webhooks", max_length=500)
    
    # Mapeo de campos personalizables
    job_id_field: str = Field(default="job_id", max_length=100)
    candidate_id_field: str = Field(default="candidate_id", max_length=100)
    status_field: str = Field(default="status", max_length=100)
    
    @field_validator('api_url')
    @classmethod
    def validate_api_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("API URL debe comenzar con http:// o https://")
        return v


class LLMConfig(BaseModel):
    """Configuración de LLM."""
    provider: str = Field(default="openai", max_length=50)
    api_key: str = Field(..., max_length=500)
    model: str = Field(default="gpt-4o-mini", max_length=100)
    max_tokens: int = Field(default=2000, ge=1, le=8000)
    temperature: float = Field(default=0.0, ge=0, le=2)
    
    # Versionado de prompts
    prompt_version: str = Field(default="v1.0", max_length=20)


class EmailConfig(BaseModel):
    """Configuración de Email (SMTP)."""
    provider: str = Field(default="smtp", max_length=50)
    smtp_host: str = Field(..., max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str = Field(..., max_length=255)
    smtp_password: str = Field(..., max_length=500)
    use_tls: bool = True
    default_from: EmailStr
    default_from_name: str = Field(default="Top Management", max_length=255)


class SystemStatus(BaseModel):
    """Estado del sistema e integraciones."""
    database: bool
    redis: bool
    whatsapp: Optional[bool] = None
    zoho: Optional[bool] = None
    llm: Optional[bool] = None
    email: Optional[bool] = None


# ============== USER SCHEMAS ==============

class UserBase(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=25)
    
    @field_validator('full_name')
    @classmethod
    def sanitize_and_validate_full_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        if len(v) > 255:
            raise ValueError("El nombre no puede exceder 255 caracteres")
        
        # Validar que no contenga HTML
        v = validate_no_html(v)
        
        # Sanitizar
        v = sanitize_string(v, max_length=255)
        
        return v.strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone_number(cls, v):
        if v:
            return validate_phone(v)
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="consultant", max_length=50)
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if len(v) > 128:
            raise ValueError("La contraseña no puede exceder 128 caracteres")
        
        # Verificar complejidad mínima
        if not re.search(r'[A-Z]', v):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        if not re.search(r'[a-z]', v):
            raise ValueError("La contraseña debe contener al menos una minúscula")
        if not re.search(r'\d', v):
            raise ValueError("La contraseña debe contener al menos un número")
        
        return v
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ['admin', 'consultant', 'viewer', 'manager']
        if v not in allowed_roles:
            raise ValueError(f"Rol no válido. Debe ser uno de: {', '.join(allowed_roles)}")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(None, max_length=255)
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=25)
    role: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=50)
    
    @field_validator('full_name')
    @classmethod
    def sanitize_full_name(cls, v):
        if v:
            v = validate_no_html(v)
            v = sanitize_string(v, max_length=255)
            if len(v.strip()) < 2:
                raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v.strip() if v else v
    
    @field_validator('phone')
    @classmethod
    def validate_phone_number(cls, v):
        if v:
            return validate_phone(v)
        return v


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
    access_token: str = Field(..., max_length=2000)
    refresh_token: str = Field(..., max_length=2000)
    token_type: str = Field(default="bearer", max_length=20)
    expires_in: int = Field(..., ge=0)


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if len(v) > 128:
            raise ValueError("La contraseña no puede exceder 128 caracteres")
        if not re.search(r'[A-Z]', v):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        if not re.search(r'[a-z]', v):
            raise ValueError("La contraseña debe contener al menos una minúscula")
        if not re.search(r'\d', v):
            raise ValueError("La contraseña debe contener al menos un número")
        return v


class EmailChange(BaseModel):
    new_email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., max_length=2000)
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if len(v) > 128:
            raise ValueError("La contraseña no puede exceder 128 caracteres")
        if not re.search(r'[A-Z]', v):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        if not re.search(r'[a-z]', v):
            raise ValueError("La contraseña debe contener al menos una minúscula")
        if not re.search(r'\d', v):
            raise ValueError("La contraseña debe contener al menos un número")
        return v


# ============== JOB OPENING SCHEMAS ==============

class JobRequirements(BaseModel):
    """Requisitos estructurados de un job para matching con IA."""
    required_skills: List[str] = Field(default=[], max_length=100)
    preferred_skills: List[str] = Field(default=[], max_length=100)
    min_years_experience: Optional[int] = Field(None, ge=0, le=50)
    education_level: Optional[str] = Field(None, max_length=50)
    education_fields: List[str] = Field(default=[], max_length=20)
    languages: List[Dict[str, str]] = Field(default=[], max_length=10)
    certifications: List[str] = Field(default=[], max_length=50)


class JobOpeningBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., max_length=10000)
    department: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    seniority: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=100)
    requirements: Optional[JobRequirements] = None
    salary_range_min: Optional[int] = Field(None, ge=0)
    salary_range_max: Optional[int] = Field(None, ge=0)
    employment_type: Optional[str] = Field(default="full-time", max_length=50)
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError("El título debe tener al menos 3 caracteres")
        if len(v) > 255:
            raise ValueError("El título no puede exceder 255 caracteres")
        v = validate_no_html(v)
        return sanitize_string(v, max_length=255)
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if not v:
            raise ValueError("La descripción es requerida")
        if len(v) > 10000:
            raise ValueError("La descripción no puede exceder 10000 caracteres")
        return sanitize_string(v, max_length=10000)
    
    @field_validator('department', 'location', 'seniority', 'sector')
    @classmethod
    def sanitize_optional_fields(cls, v):
        if v:
            v = validate_no_html(v)
            return sanitize_string(v, max_length=200)
        return v
    
    @field_validator('employment_type')
    @classmethod
    def validate_employment_type(cls, v):
        if v:
            allowed = ['full-time', 'part-time', 'contract', 'freelance', 'internship']
            if v not in allowed:
                raise ValueError(f"Tipo de empleo inválido. Debe ser: {', '.join(allowed)}")
        return v
    
    @field_validator('salary_range_max')
    @classmethod
    def validate_salary_range(cls, v, values):
        if v and values.data.get('salary_range_min') and v < values.data['salary_range_min']:
            raise ValueError("El salario máximo debe ser mayor que el mínimo")
        return v


class JobOpeningCreate(JobOpeningBase):
    assigned_consultant_id: Optional[str] = Field(None, max_length=50)
    
    @field_validator('assigned_consultant_id')
    @classmethod
    def validate_consultant_id(cls, v):
        if v:
            return validate_uuid(v)
        return v


class JobOpeningUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=10000)
    department: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    seniority: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=100)
    requirements: Optional[JobRequirements] = None
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v:
            if len(v.strip()) < 3:
                raise ValueError("El título debe tener al menos 3 caracteres")
            v = validate_no_html(v)
            return sanitize_string(v, max_length=255)
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v:
            if len(v) > 10000:
                raise ValueError("La descripción no puede exceder 10000 caracteres")
            return sanitize_string(v, max_length=10000)
        return v
    
    @field_validator('department', 'location', 'seniority', 'sector')
    @classmethod
    def sanitize_optional_fields(cls, v):
        if v:
            v = validate_no_html(v)
            return sanitize_string(v, max_length=200)
        return v
    
    @field_validator('assigned_consultant_id', check_fields=False)
    @classmethod
    def validate_consultant_id(cls, v):
        if v:
            return validate_uuid(v)
        return v
    
    @field_validator('employment_type', check_fields=False)
    @classmethod
    def validate_employment_type_update(cls, v):
        if v:
            allowed = ['full-time', 'part-time', 'contract', 'freelance', 'internship']
            if v not in allowed:
                raise ValueError(f"Tipo de empleo inválido. Debe ser: {', '.join(allowed)}")
        return v


class JobOpeningResponse(JobOpeningBase):
    id: str
    assigned_consultant_id: Optional[str] = None
    job_description_file_id: Optional[str] = None
    zoho_job_id: Optional[str] = Field(None, max_length=100)
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'assigned_consultant_id', 'job_description_file_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


# ============== CANDIDATE SCHEMAS ==============

class CandidateBase(BaseModel):
    email: Optional[EmailStr] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=25)
    full_name: Optional[str] = Field(None, max_length=255)
    
    @field_validator('full_name')
    @classmethod
    def sanitize_full_name(cls, v):
        if v:
            v = validate_no_html(v)
            return sanitize_string(v, max_length=255)
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone_number(cls, v):
        if v:
            return validate_phone(v)
        return v


class CandidateCreate(BaseModel):
    job_opening_id: str = Field(..., max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    full_name: Optional[str] = Field(None, max_length=255)
    raw_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    source: str = Field(default="manual", max_length=50)
    extracted_skills: Optional[List[str]] = Field(default_factory=list)
    extracted_experience: Optional[Any] = Field(None)
    extracted_education: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    
    @field_validator('job_opening_id')
    @classmethod
    def validate_job_id(cls, v):
        return validate_uuid(v)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v:
            # Validar formato de email
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, v):
                raise ValueError("Formato de email inválido")
        return v
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        allowed = ['manual', 'whatsapp', 'zoho', 'odoo', 'api', 'import', 'cv_upload']
        if v not in allowed:
            raise ValueError(f"Fuente no válida. Debe ser: {', '.join(allowed)}")
        return v
    
    @field_validator('raw_data')
    @classmethod
    def validate_raw_data_size(cls, v):
        if v:
            import json
            # Limitar tamaño de raw_data
            data_str = json.dumps(v)
            if len(data_str) > 50000:  # 50KB max
                raise ValueError("Los datos raw no pueden exceder 50KB")
        return v


class CandidateUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=25)
    full_name: Optional[str] = Field(None, max_length=255)
    
    @field_validator('full_name')
    @classmethod
    def sanitize_full_name(cls, v):
        if v:
            v = validate_no_html(v)
            return sanitize_string(v, max_length=255)
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone_number(cls, v):
        if v:
            return validate_phone(v)
        return v


class CandidateResponse(CandidateBase):
    id: str
    job_opening_id: str
    status: str
    zoho_candidate_id: Optional[str] = Field(None, max_length=100)
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
    candidate_id: str = Field(..., max_length=50)
    score: float = Field(..., ge=0, le=100)
    decision: str = Field(..., max_length=50)
    strengths: Optional[List[str]] = Field(None, max_length=20)
    gaps: Optional[List[str]] = Field(None, max_length=20)
    red_flags: Optional[List[str]] = Field(None, max_length=20)
    evidence: Optional[str] = Field(None, max_length=10000)
    llm_provider: Optional[str] = Field(None, max_length=50)
    llm_model: Optional[str] = Field(None, max_length=100)
    prompt_version: Optional[str] = Field(None, max_length=20)
    
    @field_validator('candidate_id')
    @classmethod
    def validate_candidate_id(cls, v):
        return validate_uuid(v)
    
    @field_validator('decision')
    @classmethod
    def validate_decision(cls, v):
        allowed = ['approved', 'rejected', 'pending', 'maybe']
        if v not in allowed:
            raise ValueError(f"Decisión no válida. Debe ser: {', '.join(allowed)}")
        return v
    
    @field_validator('strengths', 'gaps', 'red_flags')
    @classmethod
    def validate_list_fields(cls, v):
        if v:
            if len(v) > 20:
                raise ValueError("Máximo 20 elementos permitidos")
            # Sanitizar cada elemento
            return [sanitize_string(item, max_length=500) for item in v]
        return v
    
    @field_validator('evidence')
    @classmethod
    def sanitize_evidence(cls, v):
        if v:
            return sanitize_string(v, max_length=10000)
        return v


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
    name: str = Field(..., max_length=100)
    type: str = Field(..., max_length=20)  # whatsapp, email
    subject: Optional[str] = Field(None, max_length=255)
    body: str = Field(..., max_length=10000)
    variables: List[str] = Field(default=[], max_length=50)
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        allowed = ['whatsapp', 'email', 'sms']
        if v not in allowed:
            raise ValueError(f"Tipo no válido. Debe ser: {', '.join(allowed)}")
        return v
    
    @field_validator('name', 'subject')
    @classmethod
    def sanitize_text(cls, v):
        if v:
            v = validate_no_html(v)
            return sanitize_string(v, max_length=255)
        return v
    
    @field_validator('body')
    @classmethod
    def sanitize_body(cls, v):
        if v:
            if len(v) > 10000:
                raise ValueError("El cuerpo no puede exceder 10000 caracteres")
            # Permitir cierto HTML para templates de email pero sanitizar
            return sanitize_string(v, max_length=10000)
        return v


class SendCommunicationRequest(BaseModel):
    candidate_id: str = Field(..., max_length=50)
    template_name: str = Field(..., max_length=100)
    variables: Dict[str, str] = Field(default={}, max_length=50)
    
    @field_validator('candidate_id')
    @classmethod
    def validate_candidate_id(cls, v):
        return validate_uuid(v)
    
    @field_validator('variables')
    @classmethod
    def validate_variables(cls, v):
        if v:
            if len(v) > 50:
                raise ValueError("Máximo 50 variables permitidas")
            # Sanitizar valores
            return {k: sanitize_string(str(val), max_length=500) for k, val in v.items()}
        return v


# ============== JOB PAGINATION SCHEMAS ==============

class JobListResponse(BaseModel):
    """Respuesta paginada de ofertas."""
    items: List[JobOpeningResponse]
    total: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    pages: int
    has_next: bool
    has_prev: bool


class CandidateListResponse(BaseModel):
    """Respuesta paginada de candidatos."""
    items: List[CandidateResponse]
    total: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    pages: int
    has_next: bool
    has_prev: bool


class EvaluationListResponse(BaseModel):
    """Respuesta paginada de evaluaciones."""
    items: List[EvaluationResponse]
    total: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    pages: int
    has_next: bool
    has_prev: bool


# ============== REQUEST SCHEMAS ==============

class ChangeStatusRequest(BaseModel):
    """Request para cambiar estado."""
    status: str = Field(..., max_length=50)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("El estado es requerido")
        v = validate_no_html(v)
        return sanitize_string(v, max_length=50)


class EvaluateRequest(BaseModel):
    """Request para evaluar candidato."""
    force: bool = False  # Forzar re-evaluación


class CloseJobRequest(BaseModel):
    """Request para cerrar oferta."""
    reason: Optional[str] = Field(None, max_length=500)
    
    @field_validator('reason')
    @classmethod
    def sanitize_reason(cls, v):
        if v:
            v = validate_no_html(v)
            return sanitize_string(v, max_length=500)
        return v


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
    message: str = Field(..., max_length=500)
    success: bool = True
    
    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v):
        return sanitize_string(v, max_length=500)


class ErrorResponse(BaseModel):
    """Respuesta de error."""
    detail: str = Field(..., max_length=1000)
    error_code: Optional[str] = Field(None, max_length=50)
    field_errors: Optional[Dict[str, str]] = None
    
    @field_validator('detail')
    @classmethod
    def sanitize_detail(cls, v):
        # No sanitizar el detail para mantener mensajes útiles
        # pero limitar longitud
        if v and len(v) > 1000:
            v = v[:1000]
        return v


# Importar esquemas de RHTools
from app.schemas.rhtools import (
    # Enums
    ClientStatus, SubmissionStatus,
    DocumentType, DocumentStatus,
    MessageType, MessageStatus, MessageDirection,
    # Client schemas
    ClientBase, ClientCreate, ClientUpdate, ClientResponse, ClientListResponse,
    # Pipeline schemas
    StageRequiredFieldSchema, PipelineStageBase, PipelineStageCreate, PipelineStageUpdate,
    PipelineStageResponse, PipelineTemplateBase, PipelineTemplateCreate, PipelineTemplateUpdate,
    PipelineTemplateResponse, PipelineListResponse, ReorderStagesRequest,
    # Submission schemas
    SubmissionBase, SubmissionCreate, SubmissionUpdate, ChangeStageRequest,
    StageHistoryResponse, SubmissionResponse, SubmissionWithHistory, SubmissionListResponse,
    # Document schemas
    DocumentBase, DocumentCreate, DocumentUpdate, DocumentResponse, DocumentListResponse,
    DocumentDownloadResponse, DocumentExtractionResponse,
    # Message schemas
    MessageTemplateBase, MessageTemplateCreate, MessageTemplateUpdate, MessageTemplateResponse,
    MessageBase, MessageCreate, MessageResponse,
    # Offlimits schemas
    CandidateOfflimitsBase, CandidateOfflimitsCreate, CandidateOfflimitsUpdate,
    CandidateOfflimitsResponse, CandidateOfflimitsListResponse,
)
