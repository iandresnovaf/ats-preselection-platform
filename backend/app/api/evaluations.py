"""API endpoints para Evaluaciones."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_consultant
from app.models import User
from app.schemas import (
    EvaluationResponse,
    EvaluationListResponse,
    MessageResponse,
)
from app.services import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.get("", response_model=EvaluationListResponse)
async def list_evaluations(
    candidate_id: Optional[str] = Query(None, description="Filtrar por candidato"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Listar evaluaciones con filtros y paginación."""
    evaluation_service = EvaluationService(db)
    
    skip = (page - 1) * page_size
    evaluations, total = await evaluation_service.list_evaluations(
        candidate_id=candidate_id,
        skip=skip,
        limit=page_size,
    )
    
    pages = (total + page_size - 1) // page_size
    
    return {
        "items": evaluations,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Obtener evaluación por ID."""
    evaluation_service = EvaluationService(db)
    
    evaluation = await evaluation_service.get_by_id(evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluación no encontrada",
        )
    
    return evaluation


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluation(
    evaluation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Eliminar evaluación (solo consultor o admin)."""
    evaluation_service = EvaluationService(db)
    
    success = await evaluation_service.delete_evaluation(evaluation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluación no encontrada",
        )
    
    return None
