"""
Schemas Pydantic para el Core ATS API.
Validación de datos y serialización.
"""
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# BASE SCHEMAS
# =============================================================================

class BaseSchema(BaseModel):
    """Base para todos los schemas con configuración común."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimestampMixin(BaseSchema):
    """Mixin para created_at y updated_at."""
    created_at: datetime
    updated_at: datetime


# =============================================================================
# CANDIDATE SCHEMAS
# =============================================================================

class CandidateBase(BaseSchema):
    """Base para candidatos."""
    full_name: str = Field(..., min_length=1, max_length=500)
    national_id: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)
    linkedin_url: Optional[str] = Field(None, max_length=500)


class CandidateCreate(CandidateBase):
    """Schema para crear candidato."""
    pass


class CandidateUpdate(BaseSchema):
    """Schema para actualizar candidato."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=500)
    national_id: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)
    linkedin_url: Optional[str] = Field(None, max_length=500)


class CandidateResponse(CandidateBase, TimestampMixin):
    """Schema de respuesta para candidato."""
    candidate_id: UUID


class CandidateListResponse(BaseSchema):
    """Schema para lista de candidatos con paginación."""
    items: List[CandidateResponse]
    total: int
    page: int
    page_size: int


class CandidateWithApplicationsResponse(CandidateResponse):
    """Candidato con sus aplicaciones."""
    applications: List["ApplicationSummaryResponse"]


# =============================================================================
# CLIENT SCHEMAS
# =============================================================================

class ClientBase(BaseSchema):
    """Base para clientes."""
    client_name: str = Field(..., min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)


class ClientCreate(ClientBase):
    """Schema para crear cliente."""
    pass


class ClientUpdate(BaseSchema):
    """Schema para actualizar cliente."""
    client_name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)


class ClientResponse(ClientBase, TimestampMixin):
    """Schema de respuesta para cliente."""
    client_id: UUID


class ClientListResponse(BaseSchema):
    """Schema para lista de clientes."""
    items: List[ClientResponse]
    total: int
    page: int
    page_size: int


class ClientWithRolesResponse(ClientResponse):
    """Cliente con sus roles/vacantes."""
    roles: List["RoleSummaryResponse"]


# =============================================================================
# ROLE (VACANTE) SCHEMAS
# =============================================================================

class RoleStatus(str):
    """Enum para estatus de rol."""
    OPEN = "open"
    HOLD = "hold"
    CLOSED = "closed"


class RoleBase(BaseSchema):
    """Base para roles/vacantes."""
    role_title: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    seniority: Optional[str] = Field(None, max_length=50)
    status: str = Field(default="open", pattern="^(open|hold|closed)$")
    date_opened: Optional[date] = None
    date_closed: Optional[date] = None


class RoleCreate(RoleBase):
    """Schema para crear rol."""
    client_id: UUID
    role_description_doc_id: Optional[UUID] = None


class RoleUpdate(BaseSchema):
    """Schema para actualizar rol."""
    role_title: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    seniority: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, pattern="^(open|hold|closed)$")
    date_opened: Optional[date] = None
    date_closed: Optional[date] = None
    role_description_doc_id: Optional[UUID] = None


class RoleResponse(RoleBase, TimestampMixin):
    """Schema de respuesta para rol."""
    role_id: UUID
    client_id: UUID
    role_description_doc_id: Optional[UUID] = None


class RoleSummaryResponse(BaseSchema):
    """Resumen de rol para listas."""
    role_id: UUID
    role_title: str
    location: Optional[str]
    seniority: Optional[str]
    status: str
    date_opened: Optional[date]


class RoleListResponse(BaseSchema):
    """Schema para lista de roles."""
    items: List[RoleResponse]
    total: int
    page: int
    page_size: int


class RoleWithClientResponse(RoleResponse):
    """Rol con información del cliente."""
    client: ClientResponse


class RoleWithApplicationsResponse(RoleResponse):
    """Rol con sus aplicaciones."""
    applications: List["ApplicationSummaryResponse"]
    client: Optional[ClientResponse] = None


# =============================================================================
# APPLICATION SCHEMAS (ENTIDAD CENTRAL)
# =============================================================================

class ApplicationStage(str):
    """Enum para etapas detalladas de aplicación."""
    # Etapas iniciales
    SOURCING = "sourcing"
    SHORTLIST = "shortlist"
    TERNA = "terna"
    
    # Etapas de contacto
    CONTACT_PENDING = "contact_pending"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    NO_RESPONSE = "no_response"
    
    # Etapas de entrevista
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_DONE = "interview_done"
    
    # Etapas de oferta
    OFFER_SENT = "offer_sent"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    
    # Estados finales
    HIRED = "hired"
    DISCARDED = "discarded"


class ApplicationBase(BaseSchema):
    """Base para aplicaciones."""
    stage: str = Field(
        default="sourcing",
        pattern="^(sourcing|shortlist|terna|contact_pending|contacted|interested|not_interested|no_response|interview_scheduled|interview_done|offer_sent|offer_accepted|offer_rejected|hired|discarded)$"
    )
    hired: bool = False
    decision_date: Optional[date] = None
    overall_score: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    """Schema para crear aplicación."""
    candidate_id: UUID
    role_id: UUID


class ApplicationUpdate(BaseSchema):
    """Schema para actualizar aplicación."""
    stage: Optional[str] = Field(
        None,
        pattern="^(sourcing|shortlist|terna|contact_pending|contacted|interested|not_interested|no_response|interview_scheduled|interview_done|offer_sent|offer_accepted|offer_rejected|hired|discarded)$"
    )
    hired: Optional[bool] = None
    decision_date: Optional[date] = None
    overall_score: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class ApplicationStageUpdate(BaseSchema):
    """Schema específico para actualizar etapa."""
    stage: str = Field(
        ...,
        pattern="^(sourcing|shortlist|terna|contact_pending|contacted|interested|not_interested|no_response|interview_scheduled|interview_done|offer_sent|offer_accepted|offer_rejected|hired|discarded)$"
    )
    notes: Optional[str] = None


class ConsultantDecision(str, Enum):
    """Decisiones posibles del consultor."""
    CONTINUE = "continue"
    DISCARD = "discard"


class ConsultantDecisionUpdate(BaseSchema):
    """Schema para decisión del consultor (continuar o descartar)."""
    decision: str = Field(..., pattern="^(continue|discard)$")
    reason: Optional[str] = None


class ContactStatusUpdate(BaseSchema):
    """Schema para actualizar estado de contacto."""
    status: str = Field(
        ...,
        pattern="^(contacted|interested|not_interested|no_response)$"
    )


class SendMessageRequest(BaseSchema):
    """Schema para enviar mensaje a candidato."""
    template_id: str = Field(..., min_length=1)
    channel: str = Field(..., pattern="^(email|whatsapp)$")


class ApplicationDecisionUpdate(BaseSchema):
    """Schema específico para actualizar decisión."""
    hired: bool
    decision_date: Optional[date] = None
    overall_score: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class ApplicationResponse(ApplicationBase, TimestampMixin):
    """Schema de respuesta para aplicación."""
    application_id: UUID
    candidate_id: UUID
    role_id: UUID


class ApplicationSummaryResponse(BaseSchema):
    """Resumen de aplicación para listas."""
    application_id: UUID
    candidate_id: UUID
    role_id: UUID
    stage: str
    hired: bool
    overall_score: Optional[float]
    created_at: datetime


class ApplicationListResponse(BaseSchema):
    """Schema para lista de aplicaciones."""
    items: List[ApplicationResponse]
    total: int
    page: int
    page_size: int


class ApplicationWithDetailsResponse(ApplicationResponse):
    """Aplicación con candidato y rol completos."""
    candidate: CandidateResponse
    role: RoleWithClientResponse
    interviews_count: int = 0
    assessments_count: int = 0
    flags_count: int = 0


class ApplicationTimelineEvent(BaseSchema):
    """Evento en la timeline de una aplicación."""
    event_type: str  # 'stage_change', 'interview', 'assessment', 'flag', 'decision'
    event_date: datetime
    description: str
    metadata: Optional[Dict[str, Any]] = None


class ApplicationTimelineResponse(BaseSchema):
    """Timeline de una aplicación."""
    application_id: UUID
    events: List[ApplicationTimelineEvent]


# =============================================================================
# DOCUMENT SCHEMAS
# =============================================================================

class DocumentType(str):
    """Enum para tipos de documentos."""
    CV = "cv"
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    ROLE_PROFILE = "role_profile"
    OTHER = "other"


class DocumentBase(BaseSchema):
    """Base para documentos."""
    doc_type: str = Field(..., pattern="^(cv|interview|assessment|role_profile|other)$")
    original_filename: str = Field(..., max_length=500)


class DocumentUploadRequest(BaseSchema):
    """Request para subir documento."""
    doc_type: str = Field(..., pattern="^(cv|interview|assessment|role_profile|other)$")
    application_id: Optional[UUID] = None
    role_id: Optional[UUID] = None
    candidate_id: Optional[UUID] = None


class DocumentResponse(BaseSchema):
    """Schema de respuesta para documento."""
    document_id: UUID
    application_id: Optional[UUID]
    role_id: Optional[UUID]
    candidate_id: Optional[UUID]
    doc_type: str
    original_filename: str
    storage_uri: str
    sha256_hash: Optional[str]
    uploaded_by: Optional[str]
    uploaded_at: datetime


# =============================================================================
# INTERVIEW SCHEMAS
# =============================================================================

class InterviewBase(BaseSchema):
    """Base para entrevistas."""
    interview_date: Optional[datetime] = None
    interviewer: Optional[str] = Field(None, max_length=255)
    summary_text: Optional[str] = None


class InterviewCreate(InterviewBase):
    """Schema para crear entrevista."""
    application_id: UUID
    raw_doc_id: Optional[UUID] = None


class InterviewUpdate(BaseSchema):
    """Schema para actualizar entrevista."""
    interview_date: Optional[datetime] = None
    interviewer: Optional[str] = Field(None, max_length=255)
    summary_text: Optional[str] = None
    raw_doc_id: Optional[UUID] = None


class InterviewResponse(InterviewBase, TimestampMixin):
    """Schema de respuesta para entrevista."""
    interview_id: UUID
    application_id: UUID
    raw_doc_id: Optional[UUID]


class InterviewWithDocumentResponse(InterviewResponse):
    """Entrevista con documento asociado."""
    raw_document: Optional[DocumentResponse] = None


# =============================================================================
# ASSESSMENT SCHEMAS
# =============================================================================

class AssessmentType(str):
    """Enum para tipos de evaluaciones."""
    FACTOR_OSCURO = "factor_oscuro"
    INTELIGENCIA_EJECUTIVA = "inteligencia_ejecutiva"
    KOMPEDISC = "kompedisc"
    OTHER = "other"


class AssessmentBase(BaseSchema):
    """Base para evaluaciones."""
    assessment_type: str = Field(..., pattern="^(factor_oscuro|inteligencia_ejecutiva|kompedisc|other)$")
    assessment_date: Optional[date] = None
    sincerity_score: Optional[float] = Field(None, ge=0, le=100)


class AssessmentCreate(AssessmentBase):
    """Schema para crear evaluación."""
    application_id: UUID
    raw_pdf_id: Optional[UUID] = None


class AssessmentUpdate(BaseSchema):
    """Schema para actualizar evaluación."""
    assessment_type: Optional[str] = Field(None, pattern="^(factor_oscuro|inteligencia_ejecutiva|kompedisc|other)$")
    assessment_date: Optional[date] = None
    sincerity_score: Optional[float] = Field(None, ge=0, le=100)
    raw_pdf_id: Optional[UUID] = None


class AssessmentResponse(AssessmentBase, TimestampMixin):
    """Schema de respuesta para evaluación."""
    assessment_id: UUID
    application_id: UUID
    raw_pdf_id: Optional[UUID]


class AssessmentWithDocumentResponse(AssessmentResponse):
    """Evaluación con documento asociado."""
    raw_document: Optional[DocumentResponse] = None


# =============================================================================
# ASSESSMENT SCORE SCHEMAS (SCORES DINÁMICOS)
# =============================================================================

class AssessmentScoreBase(BaseSchema):
    """Base para scores de evaluación."""
    dimension: str = Field(..., min_length=1, max_length=100)
    value: float = Field(..., ge=0, le=100)
    unit: str = Field(default="score", max_length=20)
    source_page: Optional[int] = None


class AssessmentScoreCreate(AssessmentScoreBase):
    """Schema para crear score."""
    pass


class AssessmentScoreBatchCreate(BaseSchema):
    """Schema para crear múltiples scores en batch."""
    scores: List[AssessmentScoreCreate]


class AssessmentScoreResponse(AssessmentScoreBase):
    """Schema de respuesta para score."""
    score_id: UUID
    assessment_id: UUID
    created_at: datetime


class AssessmentWithScoresResponse(AssessmentResponse):
    """Evaluación con todos sus scores."""
    scores: List[AssessmentScoreResponse]


class ApplicationScoresSummary(BaseSchema):
    """Resumen de scores para una aplicación."""
    application_id: UUID
    assessments: List[AssessmentWithScoresResponse]
    overall_score: Optional[float]


# =============================================================================
# FLAG SCHEMAS (RIESGOS/ALERTAS)
# =============================================================================

class FlagSeverity(str):
    """Enum para severidad de flags."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FlagSource(str):
    """Enum para fuente de flags."""
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    CV = "cv"


class FlagBase(BaseSchema):
    """Base para flags."""
    category: Optional[str] = Field(None, max_length=100)
    severity: str = Field(..., pattern="^(low|medium|high)$")
    evidence: Optional[str] = None
    source: str = Field(..., pattern="^(interview|assessment|cv)$")


class FlagCreate(FlagBase):
    """Schema para crear flag."""
    application_id: UUID
    source_doc_id: Optional[UUID] = None


class FlagUpdate(BaseSchema):
    """Schema para actualizar flag."""
    category: Optional[str] = Field(None, max_length=100)
    severity: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    evidence: Optional[str] = None


class FlagResponse(FlagBase):
    """Schema de respuesta para flag."""
    flag_id: UUID
    application_id: UUID
    source_doc_id: Optional[UUID]
    created_at: datetime


class FlagListResponse(BaseSchema):
    """Lista de flags."""
    items: List[FlagResponse]
    total: int


class ApplicationFlagsSummary(BaseSchema):
    """Resumen de flags para una aplicación."""
    application_id: UUID
    flags: List[FlagResponse]
    high_count: int
    medium_count: int
    low_count: int


# =============================================================================
# REPORTS SCHEMAS
# =============================================================================

class TernaCandidateComparison(BaseSchema):
    """Comparación de candidato para terna."""
    candidate_id: UUID
    full_name: str
    overall_score: Optional[float]
    stage: str
    assessments_summary: Dict[str, Any]
    flags_summary: Dict[str, Any]
    interview_count: int


class TernaReportResponse(BaseSchema):
    """Reporte de comparación de terna."""
    role_id: UUID
    role_title: str
    candidates: List[TernaCandidateComparison]


class RoleAnalyticsMetrics(BaseSchema):
    """Métricas analíticas de una vacante."""
    total_applications: int
    by_stage: Dict[str, int]
    hired_count: int
    rejected_count: int
    avg_overall_score: Optional[float]
    avg_time_to_hire_days: Optional[int]  # Promedio de días desde sourcing a hired


class RoleAnalyticsResponse(BaseSchema):
    """Reporte analítico de una vacante."""
    role_id: UUID
    role_title: str
    metrics: RoleAnalyticsMetrics


class CandidateHistoryApplication(BaseSchema):
    """Historial de aplicación para un candidato."""
    application_id: UUID
    role_title: str
    client_name: str
    stage: str
    hired: bool
    decision_date: Optional[date]
    overall_score: Optional[float]
    created_at: datetime


class CandidateHistoryResponse(BaseSchema):
    """Historial completo de un candidato."""
    candidate_id: UUID
    full_name: str
    total_applications: int
    hired_count: int
    applications: List[CandidateHistoryApplication]


# =============================================================================
# AUDIT LOG SCHEMAS
# =============================================================================

class AuditLogAction(str):
    """Enum para acciones de auditoría."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class AuditLogResponse(BaseSchema):
    """Schema de respuesta para log de auditoría."""
    audit_id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    changed_by: Optional[str]
    changed_at: datetime
    diff_json: Optional[Dict[str, Any]]


# =============================================================================
# FORWARD REFERENCES RESOLUTION
# =============================================================================

# Actualizar referencias forward
CandidateWithApplicationsResponse.model_rebuild()
ClientWithRolesResponse.model_rebuild()
RoleWithApplicationsResponse.model_rebuild()
RoleWithClientResponse.model_rebuild()
ApplicationWithDetailsResponse.model_rebuild()
