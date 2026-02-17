"""
Core ATS API - HHCandidates Router
Endpoints para gestión de candidatos.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core_ats import HHCandidate, HHApplication, HHRole, HHClient
from app.schemas.core_ats import (
    CandidateCreate, CandidateUpdate, CandidateResponse,
    CandidateListResponse, CandidateWithApplicationsResponse,
    ApplicationSummaryResponse
)

router = APIRouter(prefix="/candidates", tags=["HHCandidates"])


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(
    candidate: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crear un nuevo candidato."""
    db_candidate = HHCandidate(**candidate.model_dump())
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate


@router.get("", response_model=CandidateListResponse)
def list_candidates(
    search: Optional[str] = Query(None, description="Buscar por nombre, email o teléfono"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar candidatos con paginación y búsqueda."""
    query = db.query(HHCandidate)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (HHCandidate.full_name.ilike(search_filter)) |
            (HHCandidate.email.ilike(search_filter)) |
            (HHCandidate.phone.ilike(search_filter))
        )
    
    total = query.count()
    candidates = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return CandidateListResponse(
        items=[CandidateResponse.model_validate(c) for c in candidates],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener un candidato por ID."""
    candidate = db.query(HHCandidate).filter(HHCandidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: UUID,
    candidate_update: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Actualizar un candidato."""
    db_candidate = db.query(HHCandidate).filter(HHCandidate.candidate_id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    update_data = candidate_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_candidate, field, value)
    
    db.commit()
    db.refresh(db_candidate)
    return db_candidate


@router.get("/{candidate_id}/applications", response_model=CandidateWithApplicationsResponse)
def get_candidate_applications(
    candidate_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener candidato con todas sus aplicaciones."""
    candidate = db.query(HHCandidate).filter(HHCandidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    # Cargar aplicaciones con relaciones
    applications = db.query(HHApplication).options(
        joinedload(HHApplication.role).joinedload(HHRole.client)
    ).filter(HHApplication.candidate_id == candidate_id).all()
    
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
