"""
Core ATS API - HHRoles Router
Endpoints para gestión de vacantes/roles.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core_ats import HHRole, HHClient, HHApplication, HHCandidate, HHAssessment, HHFlag, HHInterview
from app.schemas.core_ats import (
    RoleCreate, RoleUpdate, RoleResponse,
    RoleListResponse, RoleWithApplicationsResponse,
    RoleWithClientResponse, ApplicationSummaryResponse,
    TernaCandidateComparison, TernaReportResponse,
    ClientResponse
)

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crear una nueva vacante/rol."""
    # Verificar que el cliente existe
    client = db.query(HHClient).filter(HHClient.client_id == role.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    role_data = role.model_dump()
    db_role = HHRole(**role_data)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


@router.get("", response_model=RoleListResponse)
def list_roles(
    status: Optional[str] = Query(None, description="Filtrar por estado: open, hold, closed"),
    client_id: Optional[UUID] = Query(None, description="Filtrar por cliente"),
    location: Optional[str] = Query(None, description="Filtrar por ubicación"),
    seniority: Optional[str] = Query(None, description="Filtrar por seniority"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar vacantes con filtros y paginación."""
    query = db.query(HHRole)
    
    if status:
        query = query.filter(HHRole.status == status)
    if client_id:
        query = query.filter(HHRole.client_id == client_id)
    if location:
        query = query.filter(HHRole.location.ilike(f"%{location}%"))
    if seniority:
        query = query.filter(HHRole.seniority.ilike(f"%{seniority}%"))
    
    total = query.count()
    roles = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return RoleListResponse(
        items=[RoleResponse.model_validate(r) for r in roles],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{role_id}", response_model=RoleWithClientResponse)
def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener una vacante por ID con información del cliente."""
    role = db.query(HHRole).options(
        joinedload(HHRole.client)
    ).filter(HHRole.role_id == role_id).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    return role


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: UUID,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Actualizar una vacante."""
    db_role = db.query(HHRole).filter(HHRole.role_id == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    update_data = role_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_role, field, value)
    
    # Si el estado cambia a closed, establecer date_closed
    if update_data.get('status') == 'closed' and not db_role.date_closed:
        from datetime import date
        db_role.date_closed = date.today()
    
    db.commit()
    db.refresh(db_role)
    return db_role


@router.get("/{role_id}/applications", response_model=RoleWithApplicationsResponse)
def get_role_applications(
    role_id: UUID,
    stage: Optional[str] = Query(None, description="Filtrar por etapa"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener vacante con todas sus aplicaciones."""
    role = db.query(HHRole).options(
        joinedload(HHRole.client)
    ).filter(HHRole.role_id == role_id).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    # Construir query de aplicaciones
    apps_query = db.query(HHApplication).options(
        joinedload(HHApplication.candidate)
    ).filter(HHApplication.role_id == role_id)
    
    if stage:
        apps_query = apps_query.filter(HHApplication.stage == stage)
    
    applications = apps_query.all()
    
    # Construir respuesta
    role_data = RoleResponse.model_validate(role)
    client_data = ClientResponse.model_validate(role.client) if role.client else None
    
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
    
    return RoleWithApplicationsResponse(
        **role_data.model_dump(),
        applications=applications_data,
        client=client_data
    )


@router.get("/{role_id}/terna", response_model=TernaReportResponse)
def get_role_terna(
    role_id: UUID,
    candidate_ids: Optional[List[UUID]] = Query(None, description="IDs de candidatos a comparar"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Comparador de terna - Obtener comparación de candidatos para una vacante.
    Si no se especifican candidate_ids, retorna los top candidatos en etapa 'terna'.
    """
    role = db.query(HHRole).options(
        joinedload(HHRole.client)
    ).filter(HHRole.role_id == role_id).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    # Query de aplicaciones
    apps_query = db.query(HHApplication).options(
        joinedload(HHApplication.candidate),
        joinedload(HHApplication.assessments).joinedload(HHAssessment.scores),
        joinedload(HHApplication.flags),
        joinedload(HHApplication.interviews)
    ).filter(HHApplication.role_id == role_id)
    
    if candidate_ids:
        apps_query = apps_query.filter(HHApplication.candidate_id.in_(candidate_ids))
    else:
        # Por defecto, candidatos en etapa terna o con mejor score
        apps_query = apps_query.filter(
            HHApplication.stage.in_(['terna', 'interview', 'offer'])
        ).order_by(HHApplication.overall_score.desc().nullslast())
    
    applications = apps_query.limit(5).all()
    
    # Construir comparación
    candidates_comparison = []
    for app in applications:
        candidate = app.candidate
        
        # Resumen de assessments
        assessments_summary = {}
        for assessment in app.assessments:
            scores = {s.dimension: float(s.value) for s in assessment.scores}
            assessments_summary[assessment.assessment_type.value if hasattr(assessment.assessment_type, 'value') else assessment.assessment_type] = scores
        
        # Resumen de flags
        flags_summary = {
            'high': sum(1 for f in app.flags if (f.severity.value if hasattr(f.severity, 'value') else f.severity) == 'high'),
            'medium': sum(1 for f in app.flags if (f.severity.value if hasattr(f.severity, 'value') else f.severity) == 'medium'),
            'low': sum(1 for f in app.flags if (f.severity.value if hasattr(f.severity, 'value') else f.severity) == 'low'),
        }
        
        candidates_comparison.append(TernaCandidateComparison(
            candidate_id=candidate.candidate_id,
            full_name=candidate.full_name,
            overall_score=app.overall_score,
            stage=app.stage.value if hasattr(app.stage, 'value') else app.stage,
            assessments_summary=assessments_summary,
            flags_summary=flags_summary,
            interview_count=len(app.interviews)
        ))
    
    return TernaReportResponse(
        role_id=role_id,
        role_title=role.role_title,
        candidates=candidates_comparison
    )
