"""Modelos de datos para extracción de documentos."""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Tipos de documentos soportados."""
    CV = "cv"
    RESUME = "resume"
    ASSESSMENT = "assessment"
    INTERVIEW = "interview"
    COVER_LETTER = "cover_letter"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Estados del pipeline de procesamiento."""
    UPLOADED = "uploaded"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    COMPLETED = "completed"
    ERROR = "error"
    MANUAL_REVIEW = "manual_review"
    CONFIRMED = "confirmed"


class AssessmentDimension(BaseModel):
    """Dimensión de una prueba psicométrica."""
    name: str
    value: float = Field(..., ge=0, le=100)
    description: Optional[str] = None
    category: Optional[str] = None


class AssessmentData(BaseModel):
    """Datos extraídos de una prueba psicométrica."""
    test_name: str
    test_type: Optional[str] = None
    candidate_name: Optional[str] = None
    test_date: Optional[datetime] = None
    scores: List[AssessmentDimension] = Field(default_factory=list)
    sincerity_score: Optional[float] = Field(None, ge=0, le=100)
    interpretation: Optional[str] = None
    raw_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkExperience(BaseModel):
    """Experiencia laboral extraída."""
    company: Optional[str] = None
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None
    location: Optional[str] = None


class Education(BaseModel):
    """Educación extraída."""
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False


class CVData(BaseModel):
    """Datos extraídos de un CV."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    summary: Optional[str] = None
    experience: List[WorkExperience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None


class InterviewQuote(BaseModel):
    """Cita clave de una entrevista."""
    text: str
    category: Optional[str] = None  # risk, strength, concern, etc.
    sentiment: Optional[str] = None  # positive, negative, neutral


class InterviewData(BaseModel):
    """Datos extraídos de una entrevista."""
    interview_type: Optional[str] = None
    interviewer: Optional[str] = None
    date: Optional[datetime] = None
    summary: Optional[str] = None
    key_quotes: List[InterviewQuote] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)  # riesgos detectados
    strengths: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    overall_sentiment: Optional[str] = None  # positive, negative, neutral, mixed
    recommendation: Optional[str] = None
    raw_text: Optional[str] = None


class ExtractionResult(BaseModel):
    """Resultado de la extracción de datos."""
    document_type: DocumentType
    confidence: float = Field(..., ge=0, le=1)
    data: Dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    extractor_version: str = "1.0.0"
    warnings: List[str] = Field(default_factory=list)


class ParseResult(BaseModel):
    """Resultado del parsing de un documento."""
    document_id: str
    status: ProcessingStatus
    text: str
    document_type: DocumentType
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extraction: Optional[ExtractionResult] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None


class ValidationError(BaseModel):
    """Error de validación."""
    field: str
    message: str
    severity: str = "error"  # error, warning


class ValidationResult(BaseModel):
    """Resultado de la validación de datos."""
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)
    normalized_data: Dict[str, Any] = Field(default_factory=dict)


class PipelineJob(BaseModel):
    """Job del pipeline de procesamiento."""
    job_id: str
    document_id: str
    status: ProcessingStatus
    current_step: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
