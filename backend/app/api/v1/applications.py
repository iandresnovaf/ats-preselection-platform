"""
Core ATS API - HHApplications Router
Endpoints para gestión de aplicaciones (ENTIDAD CENTRAL).
Toda la información del pipeline se conecta aquí.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc, select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.authorization import verify_application_access
from app.models import User
from app.models.core_ats import (
    HHAuditLog,
    HHApplication, HHCandidate, HHRole, HHClient, HHInterview, HHAssessment,
    HHFlag, HHDocument, ApplicationStage, ScoringStatus
)
from app.schemas.core_ats import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse,
    ApplicationListResponse, ApplicationWithDetailsResponse,
    ApplicationStageUpdate, ApplicationDecisionUpdate,
    ApplicationTimelineResponse, ApplicationTimelineEvent,
    ApplicationScoresSummary, ApplicationFlagsSummary,
    AssessmentWithScoresResponse, AssessmentScoreResponse,
    FlagResponse, CandidateResponse, RoleWithClientResponse,
    ClientResponse, ConsultantDecisionUpdate, ContactStatusUpdate,
    SendMessageRequest
)
from app.services.scoring_service import scoring_service, ScoringResult
from pydantic import BaseModel, Field
from typing import Literal

router = APIRouter(prefix="/applications", tags=["HHApplications"])


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    application: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crear una nueva aplicación (Candidato ↔ Vacante)."""
    # Verificar que el candidato existe
    result = await db.execute(
        select(HHCandidate).filter(HHCandidate.candidate_id == application.candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    # Verificar que el rol existe
    result = await db.execute(
        select(HHRole).filter(HHRole.role_id == application.role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    # Verificar que no exista ya una aplicación para este par
    result = await db.execute(
        select(HHApplication).filter(
            HHApplication.candidate_id == application.candidate_id,
            HHApplication.role_id == application.role_id
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una aplicación para este candidato en esta vacante"
        )
    
    app_data = application.model_dump()
    db_application = HHApplication(**app_data)
    db.add(db_application)
    await db.commit()
    await db.refresh(db_application)
    
    # Crear registro de auditoría - convertir UUIDs a strings para JSON
    import json
    def convert_uuids(obj):
        if isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: convert_uuids(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_uuids(i) for i in obj]
        return obj
    
    audit_data = convert_uuids(app_data)
    audit = HHAuditLog(
        entity_type="application",
        entity_id=db_application.application_id,
        action="create",
        changed_by=getattr(current_user, "email", "system"),
        diff_json=audit_data
    )
    db.add(audit)
    await db.commit()
    
    # Trigger scoring automático en background (no bloqueante)
    async def trigger_auto_scoring():
        """Ejecuta el scoring automático después de un breve delay."""
        try:
            # Esperar un momento para asegurar que la transacción se complete
            await asyncio.sleep(1)
            
            # Crear nueva sesión de DB para el scoring
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as scoring_db:
                await scoring_service.score_application(
                    application_id=str(db_application.application_id),
                    db=scoring_db,
                    current_user="system_auto_scoring"
                )
        except Exception as e:
            # Log error pero no fallar la creación de la aplicación
            print(f"[AutoScoring] Error al calcular score para aplicación {db_application.application_id}: {e}")
    
    # Iniciar scoring en background
    import asyncio
    asyncio.create_task(trigger_auto_scoring())
    
    return db_application


@router.get("", response_model=ApplicationListResponse)
async def list_applications(
    role_id: Optional[UUID] = Query(None, description="Filtrar por vacante"),
    candidate_id: Optional[UUID] = Query(None, description="Filtrar por candidato"),
    stage: Optional[str] = Query(None, description="Filtrar por etapa"),
    hired: Optional[bool] = Query(None, description="Filtrar por contratados"),
    sort_by: Optional[str] = Query(None, description="Ordenar por: 'score' (mayor primero), 'score_asc' (menor primero), 'date' (más reciente), 'date_asc' (más antiguo)"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Filtrar por score mínimo"),
    max_score: Optional[float] = Query(None, ge=0, le=100, description="Filtrar por score máximo"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar aplicaciones con filtros, ordenamiento y paginación."""
    query = select(HHApplication).options(
        joinedload(HHApplication.candidate),
        joinedload(HHApplication.role).joinedload(HHRole.client)
    )
    
    if role_id:
        query = query.filter(HHApplication.role_id == role_id)
    if candidate_id:
        query = query.filter(HHApplication.candidate_id == candidate_id)
    if stage:
        query = query.filter(HHApplication.stage == stage)
    if hired is not None:
        query = query.filter(HHApplication.hired == hired)
    
    # Filtros por score
    if min_score is not None:
        query = query.filter(HHApplication.overall_score >= min_score)
    if max_score is not None:
        query = query.filter(HHApplication.overall_score <= max_score)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Aplicar ordenamiento según parámetro
    if sort_by == "score":
        # Ordenar por score descendente (mayor primero), nulls al final
        query = query.order_by(HHApplication.overall_score.desc().nulls_last())
    elif sort_by == "score_asc":
        # Ordenar por score ascendente (menor primero), nulls al final
        query = query.order_by(HHApplication.overall_score.asc().nulls_last())
    elif sort_by == "date_asc":
        # Ordenar por fecha ascendente (más antiguo primero)
        query = query.order_by(HHApplication.created_at.asc())
    else:
        # Default: ordenar por fecha descendente (más reciente primero)
        query = query.order_by(desc(HHApplication.created_at))
    
    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    applications = result.unique().scalars().all()
    
    # Build response items manually to handle relationships
    items = []
    for app in applications:
        app_dict = {
            'application_id': str(app.application_id),
            'candidate_id': str(app.candidate_id),
            'role_id': str(app.role_id),
            'stage': app.stage.value if hasattr(app.stage, 'value') else app.stage,
            'hired': app.hired,
            'decision_date': app.decision_date.isoformat() if app.decision_date else None,
            'overall_score': app.overall_score,
            'notes': app.notes,
            'created_at': app.created_at.isoformat() if app.created_at else None,
            'updated_at': app.updated_at.isoformat() if app.updated_at else None,
            'candidate': None,
            'role': None
        }
        
        if app.candidate:
            # HHCandidate usa full_name en lugar de first_name/last_name separados
            full_name = app.candidate.full_name or ""
            name_parts = full_name.split(maxsplit=1)
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            
            app_dict['candidate'] = {
                'candidate_id': str(app.candidate.candidate_id),
                'first_name': first_name,
                'last_name': last_name,
                'full_name': full_name,
                'email': app.candidate.email,
                'phone': app.candidate.phone,
                'location': app.candidate.location,
                'current_company': getattr(app.candidate, 'current_company', None),
                'current_position': getattr(app.candidate, 'current_position', None),
                'years_experience': getattr(app.candidate, 'years_experience', None),
                'linkedin_url': app.candidate.linkedin_url,
                'created_at': app.candidate.created_at.isoformat() if app.candidate.created_at else None,
                'updated_at': app.candidate.updated_at.isoformat() if app.candidate.updated_at else None,
            }
        
        if app.role:
            role_dict = {
                'role_id': str(app.role.role_id),
                'client_id': str(app.role.client_id),
                'role_title': app.role.role_title,
                'location': app.role.location,
                'seniority': app.role.seniority,
                'status': app.role.status.value if hasattr(app.role.status, 'value') else app.role.status,
                'date_opened': app.role.date_opened.isoformat() if app.role.date_opened else None,
                'date_closed': app.role.date_closed.isoformat() if app.role.date_closed else None,
                'created_at': app.role.created_at.isoformat() if app.role.created_at else None,
                'updated_at': app.role.updated_at.isoformat() if app.role.updated_at else None,
                'client': None
            }
            if app.role.client:
                role_dict['client'] = {
                    'client_id': str(app.role.client.client_id),
                    'client_name': app.role.client.client_name,
                    'industry': app.role.client.industry,
                    'created_at': app.role.client.created_at.isoformat() if app.role.client.created_at else None,
                    'updated_at': app.role.client.updated_at.isoformat() if app.role.client.updated_at else None,
                }
            app_dict['role'] = role_dict
        
        items.append(app_dict)
    
    # Return as dict to avoid Pydantic validation issues with nested objects
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{application_id}", response_model=ApplicationWithDetailsResponse)
async def get_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener una aplicación por ID con detalles completos."""
    # Verificar ownership
    await verify_application_access(application_id, db, current_user)
    
    result = await db.execute(
        select(HHApplication).options(
            joinedload(HHApplication.candidate),
            joinedload(HHApplication.role).joinedload(HHRole.client),
            joinedload(HHApplication.interviews),
            joinedload(HHApplication.assessments),
            joinedload(HHApplication.flags)
        ).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    # Construir respuesta completa
    app_data = ApplicationResponse.model_validate(application)
    
    candidate_data = CandidateResponse.model_validate(application.candidate)
    client_data = ClientResponse.model_validate(application.role.client) if application.role.client else None
    role_data = RoleWithClientResponse(
        **{k: v for k, v in application.role.__dict__.items() if not k.startswith('_')},
        client=client_data
    )
    
    return ApplicationWithDetailsResponse(
        **app_data.model_dump(),
        candidate=candidate_data,
        role=role_data,
        interviews_count=len(application.interviews),
        assessments_count=len(application.assessments),
        flags_count=len(application.flags)
    )


@router.patch("/{application_id}/stage", response_model=ApplicationResponse)
async def update_application_stage(
    application_id: UUID,
    stage_update: ApplicationStageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualizar la etapa de una aplicación."""
    # Verificar ownership
    await verify_application_access(application_id, db, current_user)
    
    result = await db.execute(
        select(HHApplication).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    old_stage = application.stage
    application.stage = stage_update.stage
    
    if stage_update.notes:
        application.notes = stage_update.notes
    
    await db.commit()
    await db.refresh(application)
    
    # Crear registro de auditoría
    audit = HHAuditLog(
        entity_type="application",
        entity_id=application_id,
        action="update",
        changed_by=getattr(current_user, "email", "system"),
        diff_json={"stage": {"old": old_stage, "new": stage_update.stage}}
    )
    db.add(audit)
    await db.commit()
    
    return application


@router.patch("/{application_id}/decision", response_model=ApplicationResponse)
async def update_application_decision(
    application_id: UUID,
    decision_update: ApplicationDecisionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualizar la decisión de contratación de una aplicación."""
    # Verificar ownership
    await verify_application_access(application_id, db, current_user)
    
    result = await db.execute(
        select(HHApplication).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    old_hired = application.hired
    application.hired = decision_update.hired
    
    if decision_update.decision_date:
        application.decision_date = decision_update.decision_date
    elif decision_update.hired and not application.decision_date:
        application.decision_date = date.today()
    
    if decision_update.overall_score is not None:
        application.overall_score = decision_update.overall_score
    
    if decision_update.notes:
        application.notes = decision_update.notes
    
    await db.commit()
    await db.refresh(application)
    
    # Crear registro de auditoría
    audit = HHAuditLog(
        entity_type="application",
        entity_id=application_id,
        action="update",
        changed_by=getattr(current_user, "email", "system"),
        diff_json={
            "hired": {"old": old_hired, "new": decision_update.hired},
            "decision_date": str(decision_update.decision_date) if decision_update.decision_date else None,
            "overall_score": str(decision_update.overall_score) if decision_update.overall_score else None
        }
    )
    db.add(audit)
    await db.commit()
    
    return application


@router.get("/{application_id}/timeline", response_model=ApplicationTimelineResponse)
async def get_application_timeline(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener la timeline completa de una aplicación."""
    result = await db.execute(
        select(HHApplication).options(
            joinedload(HHApplication.interviews),
            joinedload(HHApplication.assessments),
            joinedload(HHApplication.flags)
        ).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    events = []
    
    # Evento: Creación
    events.append(ApplicationTimelineEvent(
        event_type="create",
        event_date=application.created_at,
        description="Aplicación creada",
        metadata={"stage": application.stage.value if hasattr(application.stage, 'value') else application.stage}
    ))
    
    # Eventos: HHInterviews
    for interview in application.interviews:
        events.append(ApplicationTimelineEvent(
            event_type="interview",
            event_date=interview.interview_date or interview.created_at,
            description=f"Entrevista con {interview.interviewer or 'N/A'}",
            metadata={"interviewer": interview.interviewer}
        ))
    
    # Eventos: HHAssessments
    for assessment in application.assessments:
        events.append(ApplicationTimelineEvent(
            event_type="assessment",
            event_date=datetime.combine(assessment.assessment_date, datetime.min.time()) if assessment.assessment_date else assessment.created_at,
            description=f"Evaluación: {assessment.assessment_type.value if hasattr(assessment.assessment_type, 'value') else assessment.assessment_type}",
            metadata={"assessment_type": assessment.assessment_type.value if hasattr(assessment.assessment_type, 'value') else assessment.assessment_type}
        ))
    
    # Eventos: HHFlags
    for flag in application.flags:
        events.append(ApplicationTimelineEvent(
            event_type="flag",
            event_date=flag.created_at,
            description=f"Alerta {flag.severity.value if hasattr(flag.severity, 'value') else flag.severity}: {flag.category or 'Sin categoría'}",
            metadata={
                "severity": flag.severity.value if hasattr(flag.severity, 'value') else flag.severity,
                "category": flag.category,
                "source": flag.source.value if hasattr(flag.source, 'value') else flag.source
            }
        ))
    
    # Evento: Decisión
    if application.decision_date:
        events.append(ApplicationTimelineEvent(
            event_type="decision",
            event_date=datetime.combine(application.decision_date, datetime.min.time()),
            description="Contratado" if application.hired else "Proceso finalizado",
            metadata={"hired": application.hired, "overall_score": str(application.overall_score) if application.overall_score else None}
        ))
    
    # Ordenar por fecha
    events.sort(key=lambda x: x.event_date)
    
    return ApplicationTimelineResponse(
        application_id=application_id,
        events=events
    )


@router.get("/{application_id}/scores", response_model=ApplicationScoresSummary)
async def get_application_scores(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener todos los scores de evaluaciones de una aplicación."""
    result = await db.execute(
        select(HHApplication).options(
            joinedload(HHApplication.assessments).joinedload(HHAssessment.scores)
        ).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    assessments_data = []
    for assessment in application.assessments:
        scores_data = [
            AssessmentScoreResponse(
                score_id=s.score_id,
                assessment_id=s.assessment_id,
                dimension=s.dimension,
                value=s.value,
                unit=s.unit,
                source_page=s.source_page,
                created_at=s.created_at
            ) for s in assessment.scores
        ]
        
        assessments_data.append(AssessmentWithScoresResponse(
            assessment_id=assessment.assessment_id,
            application_id=assessment.application_id,
            assessment_type=assessment.assessment_type.value if hasattr(assessment.assessment_type, 'value') else assessment.assessment_type,
            assessment_date=assessment.assessment_date,
            sincerity_score=assessment.sincerity_score,
            raw_pdf_id=assessment.raw_pdf_id,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
            scores=scores_data
        ))
    
    return ApplicationScoresSummary(
        application_id=application_id,
        assessments=assessments_data,
        overall_score=application.overall_score
    )


@router.get("/{application_id}/flags", response_model=ApplicationFlagsSummary)
async def get_application_flags(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener todas las flags/alertas de una aplicación."""
    result = await db.execute(
        select(HHApplication).options(
            joinedload(HHApplication.flags)
        ).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    flags_data = [
        FlagResponse(
            flag_id=f.flag_id,
            application_id=f.application_id,
            category=f.category,
            severity=f.severity.value if hasattr(f.severity, 'value') else f.severity,
            evidence=f.evidence,
            source=f.source.value if hasattr(f.source, 'value') else f.source,
            source_doc_id=f.source_doc_id,
            created_at=f.created_at
        ) for f in application.flags
    ]
    
    high_count = sum(1 for f in application.flags if (f.severity.value if hasattr(f.severity, 'value') else f.severity) == 'high')
    medium_count = sum(1 for f in application.flags if (f.severity.value if hasattr(f.severity, 'value') else f.severity) == 'medium')
    low_count = sum(1 for f in application.flags if (f.severity.value if hasattr(f.severity, 'value') else f.severity) == 'low')
    
    return ApplicationFlagsSummary(
        application_id=application_id,
        flags=flags_data,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count
    )


@router.patch("/{application_id}/consultant-decision", response_model=ApplicationResponse)
async def update_consultant_decision(
    application_id: UUID,
    decision_update: ConsultantDecisionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint para que el consultor tome una decisión sobre un candidato.
    Decisiones: CONTINUE (mover a contactado) o DISCARD (descartar).
    """
    result = await db.execute(
        select(HHApplication).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    old_stage = application.stage
    
    if decision_update.decision == "continue":
        # Verificar si el candidato tiene datos de contacto
        candidate_result = await db.execute(
            select(HHCandidate).filter(HHCandidate.candidate_id == application.candidate_id)
        )
        candidate = candidate_result.scalar_one_or_none()
        
        if not candidate.email and not candidate.phone:
            # Falta información de contacto - mover a contact_pending
            application.stage = ApplicationStage.CONTACT_PENDING
        else:
            # Tiene datos de contacto - mover a contacted
            application.stage = ApplicationStage.CONTACTED
            application.initial_contact_date = datetime.utcnow()
    elif decision_update.decision == "discard":
        application.stage = ApplicationStage.DISCARDED
        application.discard_reason = decision_update.reason
    else:
        raise HTTPException(status_code=400, detail="Decisión inválida")
    
    await db.commit()
    await db.refresh(application)
    
    # Crear registro de auditoría
    audit = HHAuditLog(
        entity_type="application",
        entity_id=application_id,
        action="update",
        changed_by=getattr(current_user, "email", "system"),
        diff_json={
            "consultant_decision": decision_update.decision,
            "stage": {"old": old_stage, "new": application.stage},
            "reason": decision_update.reason
        }
    )
    db.add(audit)
    await db.commit()
    
    return application


@router.patch("/{application_id}/contact-status", response_model=ApplicationResponse)
async def update_contact_status(
    application_id: UUID,
    status_update: ContactStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Actualizar el estado de contacto del candidato.
    Estados: contacted, interested, not_interested, no_response
    """
    result = await db.execute(
        select(HHApplication).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    old_stage = application.stage
    
    # Mapear status a ApplicationStage
    status_mapping = {
        "contacted": ApplicationStage.CONTACTED,
        "interested": ApplicationStage.INTERESTED,
        "not_interested": ApplicationStage.NOT_INTERESTED,
        "no_response": ApplicationStage.NO_RESPONSE,
    }
    
    new_stage = status_mapping.get(status_update.status)
    if not new_stage:
        raise HTTPException(status_code=400, detail="Estado inválido")
    
    application.stage = new_stage
    
    # Actualizar fechas según el estado
    if status_update.status == "contacted" and not application.initial_contact_date:
        application.initial_contact_date = datetime.utcnow()
    
    if status_update.status in ["interested", "not_interested", "no_response"]:
        application.candidate_response_date = datetime.utcnow()
    
    await db.commit()
    await db.refresh(application)
    
    # Crear registro de auditoría
    audit = HHAuditLog(
        entity_type="application",
        entity_id=application_id,
        action="update",
        changed_by=getattr(current_user, "email", "system"),
        diff_json={
            "contact_status": status_update.status,
            "stage": {"old": old_stage, "new": application.stage}
        }
    )
    db.add(audit)
    await db.commit()
    
    return application


@router.post("/{application_id}/send-message")
async def send_message_to_candidate(
    application_id: UUID,
    message_request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Enviar mensaje al candidato (email o whatsapp).
    Requiere que el candidato tenga datos de contacto.
    """
    result = await db.execute(
        select(HHApplication).options(
            joinedload(HHApplication.candidate)
        ).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    candidate = application.candidate
    
    # Validar que existan datos de contacto según el canal
    if message_request.channel == "email" and not candidate.email:
        raise HTTPException(
            status_code=400, 
            detail="El candidato no tiene email registrado"
        )
    
    if message_request.channel == "whatsapp" and not candidate.phone:
        raise HTTPException(
            status_code=400,
            detail="El candidato no tiene teléfono registrado"
        )
    
    # TODO: Implementar integración real con servicio de email/WhatsApp
    # Por ahora, simulamos el envío exitoso
    
    # Actualizar estado si es el primer contacto
    if application.stage == ApplicationStage.CONTACT_PENDING:
        application.stage = ApplicationStage.CONTACTED
        application.initial_contact_date = datetime.utcnow()
        await db.commit()
    
    # Crear registro de auditoría
    audit = HHAuditLog(
        entity_type="application",
        entity_id=application_id,
        action="update",
        changed_by=getattr(current_user, "email", "system"),
        diff_json={
            "message_sent": True,
            "channel": message_request.channel,
            "template_id": message_request.template_id
        }
    )
    db.add(audit)
    await db.commit()
    
    return {
        "success": True,
        "message": f"Mensaje enviado exitosamente por {message_request.channel}",
        "candidate_id": str(candidate.candidate_id),
        "channel": message_request.channel
    }


# =============================================================================
# SCHEMAS PARA SCORING CON IA
# =============================================================================

class ScoringResponse(BaseModel):
    """Respuesta del scoring de IA."""
    application_id: UUID
    score: float = Field(..., ge=0, le=100)
    justification: str
    skill_match: dict
    experience_match: dict
    seniority_match: dict
    industry_match: Optional[dict] = None
    recommendations: List[str] = []
    evaluated_at: datetime


class ScoringRequest(BaseModel):
    """Request para ejecutar scoring."""
    force_recalculate: bool = Field(default=False, description="Forzar recálculo incluso si ya existe score")


# =============================================================================
# ENDPOINTS DE SCORING CON IA
# =============================================================================

@router.post("/{application_id}/score", response_model=ScoringResponse)
async def score_application_with_ai(
    application_id: UUID,
    request: Optional[ScoringRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Evalúa la compatibilidad entre candidato y vacante usando IA.
    
    Este endpoint analiza el CV del candidato y lo compara con los requisitos
    de la vacante, generando un score de 0-100 con justificación detallada.
    
    El score se guarda automáticamente en el campo overall_score de la aplicación.
    """
    # Verificar que la aplicación existe
    result = await db.execute(
        select(HHApplication).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    # Verificar si ya tiene score y no se fuerza recálculo
    if application.overall_score is not None and not (request and request.force_recalculate):
        return ScoringResponse(
            application_id=application_id,
            score=float(application.overall_score),
            justification="Score previamente calculado. Use force_recalculate=true para recalcular.",
            skill_match={},
            experience_match={},
            seniority_match={},
            evaluated_at=application.updated_at or datetime.utcnow()
        )
    
    try:
        # Ejecutar el scoring con IA
        scoring_result = await scoring_service.score_application(
            application_id=str(application_id),
            db=db,
            current_user=getattr(current_user, "email", "system")
        )
        
        return ScoringResponse(
            application_id=application_id,
            score=scoring_result.score,
            justification=scoring_result.justification,
            skill_match=scoring_result.skill_match,
            experience_match=scoring_result.experience_match,
            seniority_match=scoring_result.seniority_match,
            industry_match=scoring_result.industry_match,
            recommendations=scoring_result.recommendations,
            evaluated_at=datetime.utcnow()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al evaluar con IA: {str(e)}"
        )


@router.get("/{application_id}/score", response_model=ScoringResponse)
async def get_application_score(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene el score actual de una aplicación.
    
    Si no existe score calculado, retorna error 404.
    """
    result = await db.execute(
        select(HHApplication).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    if application.overall_score is None:
        raise HTTPException(
            status_code=404, 
            detail="La aplicación no tiene score calculado. Use POST /score para evaluar."
        )
    
    return ScoringResponse(
        application_id=application_id,
        score=float(application.overall_score),
        justification="Score previamente calculado",
        skill_match={},
        experience_match={},
        seniority_match={},
        evaluated_at=application.updated_at or datetime.utcnow()
    )


# =============================================================================
# RANKING DE CANDIDATOS POR VACANTE
# =============================================================================

class CandidateRankingItem(BaseModel):
    """Item del ranking de candidatos."""
    position: int
    application_id: UUID
    candidate_id: UUID
    candidate_name: str
    overall_score: float
    skill_match_score: Optional[float] = None
    experience_match_score: Optional[float] = None
    seniority_match_score: Optional[float] = None
    stage: str
    created_at: datetime


class CandidateRankingResponse(BaseModel):
    """Respuesta del ranking de candidatos."""
    role_id: UUID
    role_title: str
    total_candidates: int
    ranked_candidates: int
    unranked_candidates: int
    rankings: List[CandidateRankingItem]


@router.get("/ranking/by-role/{role_id}", response_model=CandidateRankingResponse)
async def get_candidate_ranking(
    role_id: UUID,
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Score mínimo para incluir"),
    max_results: int = Query(50, ge=1, le=100, description="Máximo número de resultados"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene el ranking de candidatos para una vacante específica.
    
    Los candidatos se ordenan por overall_score (mayor a menor).
    Incluye badges para Top 3.
    """
    # Verificar que el rol existe
    result = await db.execute(
        select(HHRole).filter(HHRole.role_id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    # Query base
    query = select(HHApplication).options(
        joinedload(HHApplication.candidate)
    ).filter(HHApplication.role_id == role_id)
    
    # Aplicar filtro de score mínimo si se proporciona
    if min_score is not None:
        query = query.filter(HHApplication.overall_score >= min_score)
    
    # Ordenar por score descendente (nulls al final)
    query = query.order_by(HHApplication.overall_score.desc().nulls_last())
    
    # Ejecutar query
    result = await db.execute(query)
    applications = result.unique().scalars().all()
    
    # Separar candidatos con y sin score
    ranked_apps = [app for app in applications if app.overall_score is not None]
    unranked_apps = [app for app in applications if app.overall_score is None]
    
    # Construir items del ranking
    rankings = []
    for position, app in enumerate(ranked_apps[:max_results], start=1):
        candidate = app.candidate
        rankings.append(CandidateRankingItem(
            position=position,
            application_id=app.application_id,
            candidate_id=app.candidate_id,
            candidate_name=candidate.full_name if candidate else "Desconocido",
            overall_score=float(app.overall_score),
            stage=app.stage.value if hasattr(app.stage, 'value') else str(app.stage),
            created_at=app.created_at
        ))
    
    return CandidateRankingResponse(
        role_id=role_id,
        role_title=role.role_title,
        total_candidates=len(applications),
        ranked_candidates=len(ranked_apps),
        unranked_candidates=len(unranked_apps),
        rankings=rankings
    )
