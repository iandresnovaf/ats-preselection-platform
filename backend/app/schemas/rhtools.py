"""Schemas Pydantic para RHTools."""
import html
import re
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator


# ============== VALIDADORES COMPARTIDOS ==============

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitiza un string para prevenir XSS."""
    if not value:
        return value
    value = html.escape(value)
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


def validate_no_html(value: str) -> str:
    """Verifica que no haya tags HTML."""
    if not value:
        return value
    html_pattern = re.compile(r'<[^>]+>')
    if html_pattern.search(value):
        raise ValueError("El campo no debe contener HTML")
    return value


# ============== ENUMS ==============

class ClientStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class SubmissionStatus(str, Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    WITHDRAWN = "withdrawn"
    HIRED = "hired"
    REJECTED = "rejected"


class DocumentType(str, Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    PORTFOLIO = "portfolio"
    CONTRACT = "contract"
    OFFER_LETTER = "offer_letter"
    INTERVIEW_NOTES = "interview_notes"
    EVALUATION = "evaluation"
    OTHER = "other"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"


class MessageType(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    INTERNAL = "internal"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageDirection(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


# ============== CLIENT SCHEMAS ==============

class ClientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    tax_id: Optional[str] = Field(None, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    sector: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=1000)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        v = validate_no_html(v)
        return sanitize_string(v, max_length=255)
    
    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("La URL debe comenzar con http:// o https://")
        return v


class ClientCreate(ClientBase):
    owner_user_id: Optional[str] = Field(None, max_length=50)
    settings: Optional[Dict[str, Any]] = None
    
    @field_validator('owner_user_id')
    @classmethod
    def validate_owner_id(cls, v):
        if v:
            return validate_uuid(v)
        return v


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    tax_id: Optional[str] = Field(None, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    sector: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=1000)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=20)
    owner_user_id: Optional[str] = Field(None, max_length=50)
    settings: Optional[Dict[str, Any]] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v:
            if len(v.strip()) < 2:
                raise ValueError("El nombre debe tener al menos 2 caracteres")
            v = validate_no_html(v)
            return sanitize_string(v, max_length=255)
        return v


class ClientResponse(ClientBase):
    id: str
    status: str
    owner_user_id: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'owner_user_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class ClientListResponse(BaseModel):
    items: List[ClientResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


# ============== PIPELINE SCHEMAS ==============

class StageRequiredFieldSchema(BaseModel):
    id: Optional[str] = None
    field_name: str = Field(..., min_length=1, max_length=100)
    field_type: str = Field(default="text", max_length=50)
    field_label: Optional[str] = Field(None, max_length=255)
    is_required: bool = True
    validation_rules: Optional[Dict[str, Any]] = None
    help_text: Optional[str] = Field(None, max_length=500)
    default_value: Optional[str] = Field(None, max_length=500)
    order_index: int = 0


class PipelineStageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    color: str = Field(default="#3B82F6", max_length=7)
    is_required: bool = False
    is_final: bool = False
    sla_hours: Optional[int] = Field(None, ge=0)
    auto_advance: bool = False
    order_index: int = 0


class PipelineStageCreate(PipelineStageBase):
    required_fields: Optional[List[StageRequiredFieldSchema]] = []


class PipelineStageUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    color: Optional[str] = Field(None, max_length=7)
    is_required: Optional[bool] = None
    is_final: Optional[bool] = None
    sla_hours: Optional[int] = Field(None, ge=0)
    auto_advance: Optional[bool] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class PipelineStageResponse(PipelineStageBase):
    id: str
    pipeline_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    required_fields: List[StageRequiredFieldSchema] = []
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'pipeline_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class PipelineTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    pipeline_type: str = Field(default="recruitment", max_length=50)
    is_default: bool = False


class PipelineTemplateCreate(PipelineTemplateBase):
    client_id: str
    stages: Optional[List[PipelineStageCreate]] = []
    
    @field_validator('client_id')
    @classmethod
    def validate_client_id(cls, v):
        return validate_uuid(v)


class PipelineTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class PipelineTemplateResponse(PipelineTemplateBase):
    id: str
    client_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    stages: List[PipelineStageResponse] = []
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'client_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class PipelineListResponse(BaseModel):
    items: List[PipelineTemplateResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


class ReorderStagesRequest(BaseModel):
    stage_ids: List[str]
    
    @field_validator('stage_ids')
    @classmethod
    def validate_stage_ids(cls, v):
        if not v:
            raise ValueError("Debe proporcionar al menos un stage")
        return [validate_uuid(sid) for sid in v]


# ============== SUBMISSION SCHEMAS ==============

class SubmissionBase(BaseModel):
    candidate_id: str
    client_id: str
    job_opening_id: str
    pipeline_id: Optional[str] = None
    priority: str = Field(default="normal", max_length=20)
    salary_expectation: Optional[float] = None
    currency: str = Field(default="USD", max_length=3)
    source: str = Field(default="manual", max_length=50)
    source_detail: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=5000)
    custom_fields: Optional[Dict[str, Any]] = None
    
    @field_validator('candidate_id', 'client_id', 'job_opening_id')
    @classmethod
    def validate_ids(cls, v):
        return validate_uuid(v)
    
    @field_validator('pipeline_id')
    @classmethod
    def validate_pipeline_id(cls, v):
        if v:
            return validate_uuid(v)
        return v


class SubmissionCreate(SubmissionBase):
    pass


class SubmissionUpdate(BaseModel):
    priority: Optional[str] = Field(None, max_length=20)
    salary_expectation: Optional[float] = None
    salary_offered: Optional[float] = None
    currency: Optional[str] = Field(None, max_length=3)
    status: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = Field(None, max_length=5000)
    custom_fields: Optional[Dict[str, Any]] = None
    owner_user_id: Optional[str] = None


class ChangeStageRequest(BaseModel):
    stage_id: str
    notes: Optional[str] = Field(None, max_length=2000)
    reason: Optional[str] = Field(None, max_length=255)
    captured_data: Optional[Dict[str, Any]] = None
    
    @field_validator('stage_id')
    @classmethod
    def validate_stage_id(cls, v):
        return validate_uuid(v)


class StageHistoryResponse(BaseModel):
    id: str
    submission_id: str
    from_stage_id: Optional[str] = None
    to_stage_id: str
    changed_by: Optional[str] = None
    changed_at: datetime
    notes: Optional[str] = None
    reason: Optional[str] = None
    captured_data: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[int] = None
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'submission_id', 'from_stage_id', 'to_stage_id', 'changed_by', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class SubmissionResponse(BaseModel):
    id: str
    candidate_id: str
    client_id: str
    job_opening_id: str
    pipeline_id: Optional[str] = None
    current_stage_id: Optional[str] = None
    status: str
    priority: str
    salary_expectation: Optional[float] = None
    salary_offered: Optional[float] = None
    currency: str
    source: str
    source_detail: Optional[str] = None
    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None
    owner_user_id: Optional[str] = None
    applied_at: datetime
    first_contact_at: Optional[datetime] = None
    interview_scheduled_at: Optional[datetime] = None
    offer_sent_at: Optional[datetime] = None
    hired_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'candidate_id', 'client_id', 'job_opening_id', 'pipeline_id', 'current_stage_id', 'owner_user_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class SubmissionWithHistory(SubmissionResponse):
    stage_history: List[StageHistoryResponse] = []


class SubmissionListResponse(BaseModel):
    items: List[SubmissionResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


# ============== DOCUMENT SCHEMAS ==============

class DocumentBase(BaseModel):
    original_filename: str = Field(..., max_length=500)
    document_type: str = Field(default=DocumentType.OTHER.value, max_length=50)
    document_category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = None
    is_private: bool = False


class DocumentCreate(DocumentBase):
    submission_id: Optional[str] = None
    candidate_id: Optional[str] = None
    client_id: Optional[str] = None
    
    @field_validator('submission_id', 'candidate_id', 'client_id')
    @classmethod
    def validate_ids(cls, v):
        if v:
            return validate_uuid(v)
        return v


class DocumentUpdate(BaseModel):
    document_type: Optional[str] = Field(None, max_length=50)
    document_category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = None
    is_private: Optional[bool] = None
    is_shared_with_candidate: Optional[bool] = None


class DocumentResponse(DocumentBase):
    id: str
    submission_id: Optional[str] = None
    candidate_id: Optional[str] = None
    client_id: Optional[str] = None
    storage_filename: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    status: str
    is_shared_with_candidate: bool
    uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'submission_id', 'candidate_id', 'client_id', 'uploaded_by', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


class DocumentDownloadResponse(BaseModel):
    download_url: str
    expires_in: int  # Segundos
    filename: str


class DocumentExtractionResponse(BaseModel):
    id: str
    document_id: str
    status: str
    extracted_text: Optional[str] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    parsed_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    extraction_engine: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============== MESSAGE SCHEMAS ==============

class MessageTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    message_type: str = Field(default=MessageType.EMAIL.value, max_length=20)
    subject: Optional[str] = Field(None, max_length=500)
    body_text: str = Field(..., min_length=1, max_length=10000)
    body_html: Optional[str] = Field(None, max_length=20000)
    variables: Optional[List[str]] = None
    category: Optional[str] = Field(None, max_length=50)


class MessageTemplateCreate(MessageTemplateBase):
    pass


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    subject: Optional[str] = Field(None, max_length=500)
    body_text: Optional[str] = Field(None, max_length=10000)
    body_html: Optional[str] = Field(None, max_length=20000)
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None


class MessageTemplateResponse(MessageTemplateBase):
    id: str
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'created_by', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class MessageBase(BaseModel):
    message_type: str = Field(default=MessageType.EMAIL.value, max_length=20)
    subject: Optional[str] = Field(None, max_length=500)
    body_text: str = Field(..., min_length=1, max_length=10000)
    to_address: str = Field(..., max_length=255)


class MessageCreate(BaseModel):
    submission_id: Optional[str] = None
    candidate_id: Optional[str] = None
    template_id: Optional[str] = None
    message_type: str = Field(default=MessageType.EMAIL.value, max_length=20)
    subject: Optional[str] = Field(None, max_length=500)
    body_text: str = Field(..., min_length=1, max_length=10000)
    variables: Optional[Dict[str, str]] = None
    scheduled_at: Optional[datetime] = None
    
    @field_validator('submission_id', 'candidate_id', 'template_id')
    @classmethod
    def validate_ids(cls, v):
        if v:
            return validate_uuid(v)
        return v


class MessageResponse(BaseModel):
    id: str
    submission_id: Optional[str] = None
    candidate_id: Optional[str] = None
    template_id: Optional[str] = None
    message_type: str
    direction: str
    subject: Optional[str] = None
    body_text: Optional[str] = None
    to_address: Optional[str] = None
    from_address: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    error_message: Optional[str] = None
    sent_by: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'submission_id', 'candidate_id', 'template_id', 'sent_by', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


# ============== OFFLIMITS SCHEMAS ==============

class CandidateOfflimitsBase(BaseModel):
    candidate_id: str
    client_id: str
    reason: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = Field(None, max_length=2000)
    expires_at: Optional[datetime] = None
    auto_expire: bool = True
    
    @field_validator('candidate_id', 'client_id')
    @classmethod
    def validate_ids(cls, v):
        return validate_uuid(v)


class CandidateOfflimitsCreate(CandidateOfflimitsBase):
    pass


class CandidateOfflimitsUpdate(BaseModel):
    reason: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = Field(None, max_length=2000)
    expires_at: Optional[datetime] = None
    auto_expire: Optional[bool] = None
    is_active: Optional[bool] = None


class CandidateOfflimitsResponse(CandidateOfflimitsBase):
    id: str
    starts_at: datetime
    is_active: bool
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expired_at: Optional[datetime] = None
    days_until_expiry: int = 0
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'candidate_id', 'client_id', 'created_by', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class CandidateOfflimitsListResponse(BaseModel):
    items: List[CandidateOfflimitsResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


# ============== DOCUMENT RESPONSE SCHEMAS (Additional) ==============

class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    mime_type: str
    file_size: int
    status: str
    message: str
    
    class Config:
        from_attributes = True
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


# Alias para compatibilidad
DocumentTextExtractionResponse = DocumentExtractionResponse


# ============== RESUME PARSE SCHEMAS ==============

class ResumeParseRequest(BaseModel):
    document_id: str
    force_reparse: bool = False
    
    @field_validator('document_id')
    @classmethod
    def validate_document_id(cls, v):
        return validate_uuid(v)


class ResumeParseResponse(BaseModel):
    id: str
    document_id: str
    candidate_id: Optional[str] = None
    parsed_json: Dict[str, Any]
    confidence_score: float
    model_id: str
    model_version: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_validator('id', 'document_id', 'candidate_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class ResumeParseUpdate(BaseModel):
    parsed_json: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    
    @field_validator('confidence_score')
    @classmethod
    def validate_score(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError("Confidence score must be between 0 and 1")
        return v


# ============== VALIDATION SCHEMAS ==============

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
