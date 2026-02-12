"""API endpoints para Matching IA entre Candidatos y Jobs.

Endpoints:
- POST /matching/analyze - Analizar match entre candidato y job
- GET /matching/candidate/{id}/jobs - Mejores jobs para un candidato
- GET /matching/job/{id}/candidates - Mejores candidatos para un job
- POST /matching/batch - Análisis batch de múltiples candidatos
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, BackgroundTasks
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cache import cache
from app.core.deps import get_current_active_user, require_consultant, require_viewer
from app.core.rate_limit import RateLimitByUser
from app.models import User
from app.services import MatchingService

router = APIRouter(prefix="/matching", tags=["Matching"])
security = HTTPBearer()


# ============== SCHEMAS ==============

class MatchAnalyzeRequest(BaseModel):
    """Request para analizar match entre candidato y job."""
    candidate_id: str = Field(..., description="ID del candidato", max_length=50)
    job_id: str = Field(..., description="ID del job", max_length=50)
    force_refresh: bool = Field(default=False, description="Forzar re-análisis ignorando cache")
    
    @field_validator('candidate_id', 'job_id')
    @classmethod
    def validate_uuid(cls, v):
        import uuid
        try:
            uuid.UUID(str(v))
            return str(v)
        except ValueError:
            raise ValueError("Formato UUID inválido")


class MatchResultResponse(BaseModel):
    """Respuesta del análisis de matching."""
    candidate_id: str
    job_id: str
    match_result_id: Optional[str] = None
    score: float = Field(..., ge=0, le=100)
    recommendation: str  # PROCEED, REVIEW, REJECT
    reasoning: str
    match_details: dict
    experience_match: dict
    education_match: dict
    strengths: List[str]
    gaps: List[str]
    red_flags: List[str]
    analyzed_at: str
    is_cached: bool


class JobMatchItem(BaseModel):
    """Item de job con score de matching."""
    job_id: str
    job_title: str
    department: Optional[str]
    location: Optional[str]
    score: float
    recommendation: str
    analyzed_at: Optional[str]


class CandidateMatchItem(BaseModel):
    """Item de candidato con score de matching."""
    candidate_id: str
    full_name: Optional[str]
    email: Optional[str]
    score: float
    recommendation: str
    strengths: List[str]
    gaps: List[str]
    analyzed_at: Optional[str]


class CandidateJobsResponse(BaseModel):
    """Respuesta de jobs recomendados para un candidato."""
    candidate_id: str
    total: int
    jobs: List[JobMatchItem]


class JobCandidatesResponse(BaseModel):
    """Respuesta de candidatos recomendados para un job."""
    job_id: str
    total: int
    candidates: List[CandidateMatchItem]


class BatchAnalyzeRequest(BaseModel):
    """Request para análisis batch."""
    candidate_ids: List[str] = Field(..., max_length=100)
    job_id: str = Field(..., max_length=50)
    
    @field_validator('candidate_ids')
    @classmethod
    def validate_candidate_ids(cls, v):
        import uuid
        if len(v) > 100:
            raise ValueError("Máximo 100 candidatos por batch")
        for cid in v:
            try:
                uuid.UUID(str(cid))
            except ValueError:
                raise ValueError(f"ID inválido: {cid}")
        return v
    
    @field_validator('job_id')
    @classmethod
    def validate_job_id(cls, v):
        import uuid
        try:
            uuid.UUID(str(v))
            return str(v)
        except ValueError:
            raise ValueError("Formato UUID inválido")


class BatchAnalyzeItem(BaseModel):
    """Item de resultado batch."""
    candidate_id: str
    success: bool
    result: Optional[MatchResultResponse] = None
    error: Optional[str] = None


class BatchAnalyzeResponse(BaseModel):
    """Respuesta de análisis batch."""
    job_id: str
    total_processed: int
    successful: int
    failed: int
    results: List[BatchAnalyzeItem]


# ============== RATE LIMITERS ==============

# Rate limit específico para endpoints de IA (más restrictivo por costos)
ai_rate_limit = RateLimitByUser(requests=10, window=60, key_prefix="matching_ai")


# ============== HELPERS ==============

async def check_candidate_access(candidate_id: str, user: User, db: AsyncSession) -> bool:
    """Verifica que el usuario tiene acceso al candidato."""
    from app.services import CandidateService
    
    candidate_service = CandidateService(db)
    candidate = await candidate_service.get_by_id(candidate_id)
    
    if not candidate:
        return False
    
    # Admin tiene acceso a todo
    if user.role == "super_admin":
        return True
    
    # Consultor tiene acceso a candidatos de sus jobs asignados
    if user.role == "consultant":
        from app.services import JobService
        job_service = JobService(db)
        job = await job_service.get_by_id(str(candidate.job_opening_id))
        if job and str(job.assigned_consultant_id) == str(user.id):
            return True
    
    # Viewer tiene acceso de lectura
    if user.role == "viewer":
        return True
    
    return False


async def check_job_access(job_id: str, user: User, db: AsyncSession) -> bool:
    """Verifica que el usuario tiene acceso al job."""
    from app.services import JobService
    
    job_service = JobService(db)
    job = await job_service.get_by_id(job_id)
    
    if not job:
        return False
    
    # Admin tiene acceso a todo
    if user.role == "super_admin":
        return True
    
    # Consultor tiene acceso a sus jobs asignados
    if user.role == "consultant":
        if str(job.assigned_consultant_id) == str(user.id):
            return True
    
    # Viewer tiene acceso de lectura
    if user.role == "viewer":
        return True
    
    return False


def get_client_ip(request: Request) -> str:
    """Obtiene la IP real del cliente."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


# ============== ENDPOINTS ==============

@router.post("/analyze", response_model=MatchResultResponse)
async def analyze_match(
    request: Request,
    data: MatchAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """
    Analiza el match entre un candidato y un job usando IA.
    
    - Requiere permisos de consultor o admin
    - Rate limit: 10 requests/minuto por usuario (costos de IA)
    - Usa cache por 24 horas (mismo CV + Job = mismo resultado)
    - Registra auditoría de quién realizó el análisis
    
    Returns:
        MatchResultResponse con score, recomendación y análisis detallado
    """
    # Rate limiting por usuario
    rate_limit_response = await ai_rate_limit(request)
    if rate_limit_response:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas solicitudes de análisis. Límite: 10/minuto."
        )
    
    # Validar acceso al candidato y job
    if not await check_candidate_access(data.candidate_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a este candidato"
        )
    
    if not await check_job_access(data.job_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a este job"
        )
    
    # Realizar análisis
    matching_service = MatchingService(db, cache=cache)
    
    try:
        result = await matching_service.analyze_match(
            candidate_id=data.candidate_id,
            job_id=data.job_id,
            user_id=str(current_user.id),
            force_refresh=data.force_refresh,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )
        
        return MatchResultResponse(**result)
        
    except Exception as e:
        # No exponer detalles de error interno en producción
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en análisis de matching: {error_msg}"
        )


@router.get("/candidate/{candidate_id}/jobs", response_model=CandidateJobsResponse)
async def get_best_jobs_for_candidate(
    candidate_id: str,
    limit: int = Query(10, ge=1, le=50),
    min_score: float = Query(0.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
):
    """
    Obtiene los jobs con mejor match para un candidato.
    
    - Requiere permisos de viewer, consultor o admin
    - Ordenado por score descendente
    - Solo incluye jobs con análisis previo
    
    Args:
        candidate_id: ID del candidato
        limit: Máximo de resultados (1-50)
        min_score: Score mínimo para incluir (0-100)
    
    Returns:
        Lista de jobs ordenados por score de matching
    """
    # Validar acceso
    if not await check_candidate_access(candidate_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a este candidato"
        )
    
    matching_service = MatchingService(db, cache=cache)
    
    jobs = await matching_service.get_best_jobs_for_candidate(
        candidate_id=candidate_id,
        limit=limit,
        min_score=min_score
    )
    
    return CandidateJobsResponse(
        candidate_id=candidate_id,
        total=len(jobs),
        jobs=[JobMatchItem(**job) for job in jobs]
    )


@router.get("/job/{job_id}/candidates", response_model=JobCandidatesResponse)
async def get_best_candidates_for_job(
    job_id: str,
    limit: int = Query(20, ge=1, le=100),
    min_score: float = Query(0.0, ge=0, le=100),
    recommendation: Optional[str] = Query(None, description="Filtrar por recomendación: PROCEED, REVIEW, REJECT"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
):
    """
    Obtiene los candidatos con mejor match para un job.
    
    - Requiere permisos de viewer, consultor o admin
    - Ordenado por score descendente
    - Puede filtrar por recomendación específica
    
    Args:
        job_id: ID del job
        limit: Máximo de resultados (1-100)
        min_score: Score mínimo para incluir (0-100)
        recommendation: Filtrar por PROCEED, REVIEW o REJECT
    
    Returns:
        Lista de candidatos ordenados por score de matching
    """
    # Validar recomendación si se proporciona
    if recommendation and recommendation not in ["PROCEED", "REVIEW", "REJECT"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recomendación inválida. Debe ser: PROCEED, REVIEW o REJECT"
        )
    
    # Validar acceso
    if not await check_job_access(job_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a este job"
        )
    
    matching_service = MatchingService(db, cache=cache)
    
    candidates = await matching_service.get_best_candidates_for_job(
        job_id=job_id,
        limit=limit,
        min_score=min_score,
        recommendation=recommendation
    )
    
    return JobCandidatesResponse(
        job_id=job_id,
        total=len(candidates),
        candidates=[CandidateMatchItem(**c) for c in candidates]
    )


@router.post("/batch", response_model=BatchAnalyzeResponse)
async def batch_analyze(
    request: Request,
    data: BatchAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """
    Analiza múltiples candidatos contra un job en batch.
    
    - Requiere permisos de consultor o admin
    - Rate limit: 10 requests/minuto por usuario
    - Máximo 100 candidatos por batch
    - Procesamiento async si toma más de 5 segundos
    
    Args:
        candidate_ids: Lista de IDs de candidatos (máx 100)
        job_id: ID del job
    
    Returns:
        Resultados del análisis para cada candidato
    """
    # Rate limiting por usuario
    rate_limit_response = await ai_rate_limit(request)
    if rate_limit_response:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas solicitudes de análisis. Límite: 10/minuto."
        )
    
    # Validar acceso al job
    if not await check_job_access(data.job_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a este job"
        )
    
    # Validar acceso a todos los candidatos
    for candidate_id in data.candidate_ids:
        if not await check_candidate_access(candidate_id, current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permiso para acceder al candidato {candidate_id}"
            )
    
    matching_service = MatchingService(db, cache=cache)
    
    results = await matching_service.batch_analyze(
        candidate_ids=data.candidate_ids,
        job_id=data.job_id,
        user_id=str(current_user.id)
    )
    
    # Convertir resultados al formato de respuesta
    response_items = []
    for r in results:
        item = BatchAnalyzeItem(
            candidate_id=r["candidate_id"],
            success=r["success"]
        )
        if r["success"]:
            item.result = MatchResultResponse(**r["result"])
        else:
            item.error = r.get("error", "Error desconocido")
        response_items.append(item)
    
    successful = sum(1 for r in results if r["success"])
    
    return BatchAnalyzeResponse(
        job_id=data.job_id,
        total_processed=len(results),
        successful=successful,
        failed=len(results) - successful,
        results=response_items
    )
