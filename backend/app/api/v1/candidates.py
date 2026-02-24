"""
Core ATS API - HHCandidates Router
Endpoints para gestión de candidatos.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_user, validate_uuid
from app.core.authorization import verify_candidate_access
from app.models import User
from app.models.core_ats import HHCandidate, HHApplication, HHRole, HHClient
from app.schemas.core_ats import (
    CandidateCreate, CandidateUpdate, CandidateResponse,
    CandidateListResponse, CandidateWithApplicationsResponse,
    ApplicationSummaryResponse
)

router = APIRouter(prefix="/candidates", tags=["HHCandidates"])


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crear un nuevo candidato."""
    db_candidate = HHCandidate(**candidate.model_dump())
    db.add(db_candidate)
    await db.commit()
    await db.refresh(db_candidate)
    return db_candidate


@router.get("", response_model=CandidateListResponse)
async def list_candidates(
    search: Optional[str] = Query(None, description="Buscar por nombre, email o teléfono"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar candidatos con paginación y búsqueda."""
    query = select(HHCandidate)
    
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (HHCandidate.full_name.ilike(search_filter)) |
            (HHCandidate.email.ilike(search_filter)) |
            (HHCandidate.phone.ilike(search_filter))
        )
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    candidates = result.scalars().all()
    
    return CandidateListResponse(
        items=[CandidateResponse.model_validate(c) for c in candidates],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener un candidato por ID."""
    # Validar UUID
    candidate_uuid = validate_uuid(candidate_id)
    
    # Verificar ownership
    await verify_candidate_access(candidate_uuid, db, current_user)
    
    result = await db.execute(
        select(HHCandidate).where(HHCandidate.candidate_id == candidate_uuid)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    candidate_update: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualizar un candidato."""
    # Validar UUID
    candidate_uuid = validate_uuid(candidate_id)
    
    # Verificar ownership
    await verify_candidate_access(candidate_uuid, db, current_user)
    
    result = await db.execute(
        select(HHCandidate).where(HHCandidate.candidate_id == candidate_uuid)
    )
    db_candidate = result.scalar_one_or_none()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    update_data = candidate_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_candidate, field, value)
    
    await db.commit()
    await db.refresh(db_candidate)
    return db_candidate


@router.get("/{candidate_id}/applications", response_model=CandidateWithApplicationsResponse)
async def get_candidate_applications(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener candidato con todas sus aplicaciones."""
    # Validar UUID
    candidate_uuid = validate_uuid(candidate_id)
    
    # Verificar ownership
    await verify_candidate_access(candidate_uuid, db, current_user)
    
    result = await db.execute(
        select(HHCandidate).where(HHCandidate.candidate_id == candidate_uuid)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    # Cargar aplicaciones
    apps_result = await db.execute(
        select(HHApplication).where(HHApplication.candidate_id == candidate_uuid)
    )
    applications = apps_result.scalars().all()
    
    # Construir respuesta
    candidate_data = CandidateResponse.model_validate(candidate)
    applications_data = [
        ApplicationSummaryResponse(
            application_id=app.application_id,
            candidate_id=app.candidate_id,
            role_id=app.role_id,
            stage=app.stage.value if hasattr(app.stage, 'value') else app.stage,
            hired=app.hired,
            overall_score=app.overall_score,
            created_at=app.created_at
        ) for app in applications
    ]
    
    return CandidateWithApplicationsResponse(
        **candidate_data.model_dump(),
        applications=applications_data
    )
