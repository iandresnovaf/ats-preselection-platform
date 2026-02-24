"""
Core ATS API - HHRoles Router
Endpoints para gestión de vacantes/roles.
"""
import tempfile
import os
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.authorization import verify_role_access
from app.models import User
from app.models.core_ats import HHRole, HHClient, HHApplication, HHCandidate, HHAssessment, HHFlag, HHInterview
from app.schemas.core_ats import (
    RoleCreate, RoleUpdate, RoleResponse,
    RoleListResponse, RoleWithApplicationsResponse,
    RoleWithClientResponse, ApplicationSummaryResponse,
    TernaCandidateComparison, TernaReportResponse,
    ClientResponse
)
from app.services.job_profile_extractor import JobProfileExtractor

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crear una nueva vacante/rol."""
    # Verificar que el cliente existe
    result = await db.execute(
        select(HHClient).where(HHClient.client_id == role.client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    role_data = role.model_dump()
    db_role = HHRole(**role_data)
    db.add(db_role)
    await db.commit()
    await db.refresh(db_role)
    return db_role


@router.get("")
async def list_roles(
    status: Optional[str] = Query(None, description="Filtrar por estado: open, hold, closed"),
    client_id: Optional[UUID] = Query(None, description="Filtrar por cliente"),
    location: Optional[str] = Query(None, description="Filtrar por ubicación"),
    seniority: Optional[str] = Query(None, description="Filtrar por seniority"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar vacantes con filtros y paginación."""
    query = select(HHRole).options(selectinload(HHRole.client))
    
    if status:
        query = query.where(HHRole.status == status)
    if client_id:
        query = query.where(HHRole.client_id == client_id)
    if location:
        query = query.where(HHRole.location.ilike(f"%{location}%"))
    if seniority:
        query = query.where(HHRole.seniority.ilike(f"%{seniority}%"))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    roles = result.unique().scalars().all()
    
    # Get all client IDs and fetch clients in one query
    client_ids = [r.client_id for r in roles]
    clients_result = await db.execute(
        select(HHClient).where(HHClient.client_id.in_(client_ids))
    )
    clients = {c.client_id: c for c in clients_result.scalars().all()}
    
    # Serialize roles with client info
    items = []
    for r in roles:
        client = clients.get(r.client_id)
        role_dict = {
            'role_id': str(r.role_id),
            'client_id': str(r.client_id),
            'role_title': r.role_title,
            'location': r.location,
            'seniority': r.seniority,
            'status': r.status.value if hasattr(r.status, 'value') else r.status,
            'date_opened': r.date_opened.isoformat() if r.date_opened else None,
            'date_closed': r.date_closed.isoformat() if r.date_closed else None,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'updated_at': r.updated_at.isoformat() if r.updated_at else None,
            'role_description_doc_id': str(r.role_description_doc_id) if r.role_description_doc_id else None,
            'client': None
        }
        if client:
            role_dict['client'] = {
                'client_id': str(client.client_id),
                'client_name': client.client_name,
                'industry': client.industry,
                'created_at': client.created_at.isoformat() if client.created_at else None,
                'updated_at': client.updated_at.isoformat() if client.updated_at else None,
            }
        items.append(role_dict)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{role_id}", response_model=RoleWithClientResponse)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener una vacante por ID con información del cliente."""
    # Verificar ownership
    await verify_role_access(role_id, db, current_user)
    
    result = await db.execute(
        select(HHRole)
        .options(selectinload(HHRole.client))
        .where(HHRole.role_id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    return role


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_update: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualizar una vacante."""
    # Verificar ownership
    await verify_role_access(role_id, db, current_user)
    
    result = await db.execute(
        select(HHRole).where(HHRole.role_id == role_id)
    )
    db_role = result.scalar_one_or_none()
    if not db_role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    update_data = role_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_role, field, value)
    
    # Si el estado cambia a closed, establecer date_closed
    if update_data.get('status') == 'closed' and not db_role.date_closed:
        from datetime import date
        db_role.date_closed = date.today()
    
    await db.commit()
    await db.refresh(db_role)
    return db_role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Eliminar una vacante solo si no tiene aplicaciones/candidatos asociados."""
    # Verificar ownership
    await verify_role_access(role_id, db, current_user)
    
    # Verificar que la vacante existe
    result = await db.execute(
        select(HHRole).where(HHRole.role_id == role_id)
    )
    db_role = result.scalar_one_or_none()
    if not db_role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    # Verificar si tiene aplicaciones asociadas
    apps_count_result = await db.execute(
        select(func.count()).where(HHApplication.role_id == role_id)
    )
    apps_count = apps_count_result.scalar()
    
    if apps_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede eliminar la vacante porque tiene {apps_count} candidato(s) asociado(s)"
        )
    
    await db.delete(db_role)
    await db.commit()
    return None


@router.get("/{role_id}/applications", response_model=RoleWithApplicationsResponse)
async def get_role_applications(
    role_id: UUID,
    stage: Optional[str] = Query(None, description="Filtrar por etapa"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener vacante con todas sus aplicaciones."""
    result = await db.execute(
        select(HHRole)
        .options(selectinload(HHRole.client))
        .where(HHRole.role_id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    # Construir query de aplicaciones
    apps_query = select(HHApplication).options(
        selectinload(HHApplication.candidate)
    ).where(HHApplication.role_id == role_id)
    
    if stage:
        apps_query = apps_query.where(HHApplication.stage == stage)
    
    apps_result = await db.execute(apps_query)
    applications = apps_result.scalars().all()
    
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
async def get_role_terna(
    role_id: UUID,
    candidate_ids: Optional[List[UUID]] = Query(None, description="IDs de candidatos a comparar"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Comparador de terna - Obtener comparación de candidatos para una vacante.
    Si no se especifican candidate_ids, retorna los top candidatos en etapa 'terna'.
    """
    result = await db.execute(
        select(HHRole)
        .options(selectinload(HHRole.client))
        .where(HHRole.role_id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    # Query de aplicaciones
    apps_query = select(HHApplication).options(
        selectinload(HHApplication.candidate),
        selectinload(HHApplication.assessments).selectinload(HHAssessment.scores),
        selectinload(HHApplication.flags),
        selectinload(HHApplication.interviews)
    ).where(HHApplication.role_id == role_id)
    
    if candidate_ids:
        apps_query = apps_query.where(HHApplication.candidate_id.in_(candidate_ids))
    else:
        # Por defecto, candidatos en etapa terna o con mejor score
        apps_query = apps_query.where(
            HHApplication.stage.in_(['terna', 'interview', 'offer'])
        ).order_by(HHApplication.overall_score.desc().nullslast())
    
    apps_result = await db.execute(apps_query.limit(5))
    applications = apps_result.scalars().all()
    
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


@router.post("/extract-from-document")
async def extract_role_from_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Extraer información de perfil de cargo desde PDF/Word.
    
    Soporta formatos: PDF, DOCX, DOC, TXT
    
    Returns:
        Dict con los datos estructurados extraídos del documento
    """
    # Validar formato del archivo
    allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
    file_ext = os.path.splitext(file.filename.lower())[1]
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {file_ext}. Use: PDF, DOCX, DOC, TXT"
        )
    
    # Crear archivo temporal
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Extraer información
        extractor = JobProfileExtractor()
        extracted_data = extractor.extract_from_document(temp_path)
        
        return {
            "success": True,
            "filename": file.filename,
            "data": extracted_data
        }
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando documento: {str(e)}")
    finally:
        # Limpiar archivo temporal
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
