"""API endpoints para Ofertas de Trabajo (Jobs)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_consultant
from app.models import User
from app.schemas import (
    JobOpeningCreate, 
    JobOpeningUpdate, 
    JobOpeningResponse,
    JobListResponse,
    CandidateListResponse,
    MessageResponse,
)
from app.services import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filtrar por estado (draft, active, closed, paused)"),
    assigned_consultant_id: Optional[str] = Query(None, description="Filtrar por consultor asignado"),
    search: Optional[str] = Query(None, description="Buscar por título, departamento o ubicación"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Listar ofertas de trabajo con filtros y paginación."""
    job_service = JobService(db)
    
    skip = (page - 1) * page_size
    jobs, total = await job_service.list_jobs(
        status=status,
        assigned_consultant_id=assigned_consultant_id,
        search=search,
        skip=skip,
        limit=page_size,
    )
    
    pages = (total + page_size - 1) // page_size
    
    return {
        "items": jobs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }


@router.post("", response_model=JobOpeningResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    data: JobOpeningCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Crear nueva oferta de trabajo (solo consultor o admin)."""
    job_service = JobService(db)
    
    job = await job_service.create_job(data)
    return job


@router.get("/{job_id}", response_model=JobOpeningResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Obtener oferta de trabajo por ID."""
    job_service = JobService(db)
    
    job = await job_service.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    return job


@router.patch("/{job_id}", response_model=JobOpeningResponse)
async def update_job(
    job_id: str,
    data: JobOpeningUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Actualizar oferta de trabajo (solo consultor o admin)."""
    job_service = JobService(db)
    
    job = await job_service.update_job(job_id, data)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Eliminar oferta de trabajo (solo consultor o admin)."""
    job_service = JobService(db)
    
    success = await job_service.delete_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    return None


@router.post("/{job_id}/close", response_model=JobOpeningResponse)
async def close_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Cerrar oferta de trabajo (solo consultor o admin)."""
    job_service = JobService(db)
    
    job = await job_service.close_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    return job


@router.get("/{job_id}/candidates", response_model=CandidateListResponse)
async def get_job_candidates(
    job_id: str,
    status: Optional[str] = Query(None, description="Filtrar por estado del candidato"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Obtener candidatos de una oferta de trabajo."""
    job_service = JobService(db)
    
    # Verificar que la oferta existe
    job = await job_service.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    skip = (page - 1) * page_size
    candidates, total = await job_service.get_job_candidates(
        job_id=job_id,
        status=status,
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
