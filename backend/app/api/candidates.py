"""API endpoints para Candidatos."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_consultant
from app.models import User, CandidateStatus
from app.schemas import (
    CandidateCreate,
    CandidateUpdate,
    CandidateResponse,
    CandidateWithEvaluation,
    CandidateListResponse,
    EvaluationResponse,
    ChangeStatusRequest,
    EvaluateRequest,
    MessageResponse,
)
from app.services import CandidateService, JobService, EvaluationService

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.get("", response_model=CandidateListResponse)
async def list_candidates(
    job_opening_id: Optional[str] = Query(None, description="Filtrar por oferta de trabajo"),
    status: Optional[str] = Query(None, description="Filtrar por estado del candidato"),
    source: Optional[str] = Query(None, description="Filtrar por fuente"),
    search: Optional[str] = Query(None, description="Buscar por nombre o email"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Listar candidatos con filtros y paginación."""
    candidate_service = CandidateService(db)
    
    skip = (page - 1) * page_size
    candidates, total = await candidate_service.list_candidates(
        job_opening_id=job_opening_id,
        status=status,
        source=source,
        search=search,
        skip=skip,
        limit=page_size,
    )
    
    pages = (total + page_size - 1) // page_size
    
    return {
        "items": candidates,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    data: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Crear nuevo candidato (solo consultor o admin)."""
    candidate_service = CandidateService(db)
    job_service = JobService(db)
    
    # Verificar que la oferta existe
    job = await job_service.get_by_id(data.job_opening_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    candidate = await candidate_service.create_candidate(data)
    return candidate


@router.get("/{candidate_id}", response_model=CandidateWithEvaluation)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Obtener candidato por ID con sus evaluaciones."""
    candidate_service = CandidateService(db)
    evaluation_service = EvaluationService(db)
    
    candidate = await candidate_service.get_by_id_with_evaluations(candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidato no encontrado",
        )
    
    # Obtener evaluaciones
    evaluations = await evaluation_service.get_candidate_evaluations(candidate_id)
    
    # Obtener la evaluación más reciente
    latest = await evaluation_service.get_latest_evaluation(candidate_id)
    
    # Construir respuesta
    candidate_dict = {
        "id": str(candidate.id),
        "job_opening_id": str(candidate.job_opening_id),
        "email": candidate.email,
        "phone": candidate.phone,
        "full_name": candidate.full_name,
        "status": candidate.status,
        "zoho_candidate_id": candidate.zoho_candidate_id,
        "is_duplicate": candidate.is_duplicate,
        "duplicate_of_id": str(candidate.duplicate_of_id) if candidate.duplicate_of_id else None,
        "created_at": candidate.created_at,
        "updated_at": candidate.updated_at,
        "source": candidate.source,
        "evaluations": evaluations,
        "latest_score": latest.score if latest else None,
        "latest_decision": latest.decision if latest else None,
    }
    
    return candidate_dict


@router.patch("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    data: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Actualizar candidato (solo consultor o admin)."""
    candidate_service = CandidateService(db)
    
    candidate = await candidate_service.update_candidate(candidate_id, data)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidato no encontrado",
        )
    
    return candidate


@router.post("/{candidate_id}/evaluate", response_model=EvaluationResponse)
async def evaluate_candidate(
    candidate_id: str,
    request: EvaluateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Evaluar candidato con LLM (solo consultor o admin)."""
    candidate_service = CandidateService(db)
    job_service = JobService(db)
    evaluation_service = EvaluationService(db)
    
    # Verificar que el candidato existe
    candidate = await candidate_service.get_by_id(candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidato no encontrado",
        )
    
    # Obtener la oferta de trabajo
    job = await job_service.get_by_id(str(candidate.job_opening_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    # Verificar si ya tiene evaluación y no se fuerza re-evaluación
    if not request.force:
        latest = await evaluation_service.get_latest_evaluation(candidate_id)
        if latest:
            return latest
    
    # Configuración del LLM (hardcoded por ahora, idealmente vendría de la BD)
    llm_config = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "prompt_version": "v1.0",
    }
    
    try:
        evaluation = await candidate_service.evaluate_candidate(
            candidate_id=candidate_id,
            job_opening=job,
            llm_config=llm_config,
        )
        return evaluation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{candidate_id}/change-status", response_model=CandidateResponse)
async def change_candidate_status(
    candidate_id: str,
    request: ChangeStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Cambiar estado del candidato (solo consultor o admin)."""
    candidate_service = CandidateService(db)
    
    # Validar estado
    valid_statuses = [s.value for s in CandidateStatus]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido. Estados válidos: {', '.join(valid_statuses)}",
        )
    
    candidate = await candidate_service.change_status(candidate_id, request.status)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidato no encontrado",
        )
    
    return candidate
