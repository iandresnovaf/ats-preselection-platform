"""
Core ATS API - HHApplications Router
Endpoints para gestión de aplicaciones (ENTIDAD CENTRAL).
Toda la información del pipeline se conecta aquí.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core_ats import (
    HHAuditLog,
    HHApplication, HHCandidate, HHRole, HHClient, HHInterview, HHAssessment,
    HHFlag, HHDocument, ApplicationStage
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

router = APIRouter(prefix="/applications", tags=["HHApplications"])


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    application: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crear una nueva aplicación (Candidato ↔ Vacante)."""
    # Verificar que el candidato existe
    candidate = db.query(HHCandidate).filter(HHCandidate.candidate_id == application.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    # Verificar que el rol existe
    role = db.query(HHRole).filter(HHRole.role_id == application.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    # Verificar que no exista ya una aplicación para este par
    existing = db.query(HHApplication).filter(
        HHApplication.candidate_id == application.candidate_id,
        HHApplication.role_id == application.role_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una aplicación para este candidato en esta vacante"
        )
    
    app_data = application.model_dump()
    db_application = HHApplication(**app_data)
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    
    # Crear registro de auditoría
    audit = HHAuditLog(
        entity_type="application",
        entity_id=db_application.application_id,
        action="create",
        changed_by=current_user.get("email", "system"),
        diff_json=app_data
    )
    db.add(audit)
    db.commit()
    
    return db_application


@router.get("", response_model=ApplicationListResponse)
def list_applications(
    role_id: Optional[UUID] = Query(None, description="Filtrar por vacante"),
    candidate_id: Optional[UUID] = Query(None, description="Filtrar por candidato"),
    stage: Optional[str] = Query(None, description="Filtrar por etapa"),
    hired: Optional[bool] = Query(None, description="Filtrar por contratados"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar aplicaciones con filtros y paginación."""
    query = db.query(HHApplication)
    
    if role_id:
        query = query.filter(HHApplication.role_id == role_id)
    if candidate_id:
        query = query.filter(HHApplication.candidate_id == candidate_id)
    if stage:
        query = query.filter(HHApplication.stage == stage)
    if hired is not None:
        query = query.filter(HHApplication.hired == hired)
    
    total = query.count()
    applications = query.order_by(desc(HHApplication.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return ApplicationListResponse(
        items=[ApplicationResponse.model_validate(a) for a in applications],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{application_id}", response_model=ApplicationWithDetailsResponse)
def get_application(
    application_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener una aplicación por ID con detalles completos."""
    application = db.query(HHApplication).options(
        joinedload(HHApplication.candidate),
        joinedload(HHApplication.role).joinedload(HHRole.client),
        joinedload(HHApplication.interviews),
        joinedload(HHApplication.assessments),
        joinedload(HHApplication.flags)
    ).filter(HHApplication.application_id == application_id).first()
    
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
def update_application_stage(
    application_id: UUID,
    stage_update: ApplicationStageUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Actualizar la etapa de una aplicación."""
    application = db.query(HHApplication).filter(HHApplication.application_id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    old_stage = application.stage
    application.stage = stage_update.stage
    
    if stage_update.notes:
        application.notes = stage_update.notes
    
    db.commit()
    db.refresh(application)
    
    # Crear registro de auditoría
    audit = HHAuditLog(
        entity_type="application",
        entity_id=application_id,
        action="update",
        changed_by=current_user.get("email", "system"),
        diff_json={"stage": {"old": old_stage, "new": stage_update.stage}}
    )
    db.add(audit)
    db.commit()
    
    return application


@router.patch("/{application_id}/decision", response_model=ApplicationResponse)
def update_application_decision(
    application_id: UUID,
    decision_update: ApplicationDecisionUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Actualizar la decisión de contratación de una aplicación."""
    application = db.query(HHApplication).filter(HHApplication.application_id == application_id).first()
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
    
    db.commit()
    db.refresh(application)
    
    # Crear registro de auditoría
    audit = HHAuditLog(
        entity_type="application",
        entity_id=application_id,
        action="update",
        changed_by=current_user.get("email", "system"),
        diff_json={
            "hired": {"old": old_hired, "new": decision_update.hired},
            "decision_date": str(decision_update.decision_date) if decision_update.decision_date else None,
            "overall_score": str(decision_update.overall_score) if decision_update.overall_score else None
        }
    )
    db.add(audit)
    db.commit()
    
    return application


@router.get("/{application_id}/timeline", response_model=ApplicationTimelineResponse)
def get_application_timeline(
    application_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener la timeline completa de una aplicación."""
    application = db.query(HHApplication).filter(HHApplication.application_id == application_id).first()
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
def get_application_scores(
    application_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener todos los scores de evaluaciones de una aplicación."""
    application = db.query(HHApplication).options(
        joinedload(HHApplication.assessments).joinedload(HHAssessment.scores)
    ).filter(HHApplication.application_id == application_id).first()
    
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
def get_application_flags(
    application_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener todas las flags/alertas de una aplicación."""
    application = db.query(HHApplication).options(
        joinedload(HHApplication.flags)
    ).filter(HHApplication.application_id == application_id).first()
    
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
def update_consultant_decision(
    application_id: UUID,
    decision_update: ConsultantDecisionUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint para que el consultor tome una decisión sobre un candidato.
    Decisiones: CONTINUE (mover a contactado) o DISCARD (descartar).
    """
    application = db.query(HHApplication).filter(HHApplication.application_id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    old_stage = application.stage
    
    if decision_update.decision == "continue":
        # Verificar si el candidato tiene datos de contacto
        candidate = db.query(HHCandidate).filter(HHCandidate.candidate_id == application.candidate_id).first()
        
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
    
    db.commit()
    db.refresh(application)
    
    # Crear registro de auditoría
    audit = HHAuditLog(
        entity_type="application",
        entity_id=application_id,
        action="update",
        changed_by=current_user.get("email", "system"),
        diff_json={
            "consultant_decision": decision_update.decision,
            "stage": {"old": old_stage, "new": application.stage},
            "reason": decision_update.reason
        }
    )
    db.add(audit)
    db.commit()
    
    return application


@router.patch("/{application_id}/contact-status", response_model=ApplicationResponse)
def update_contact_status(
    application_id: UUID,
    status_update: ContactStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Actualizar el estado de contacto del candidato.
    Estados: contacted, interested, not_interested, no_response
    """
    application = db.query(HHApplication).filter(HHApplication.application_id == application_id).first()
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
    
    db.commit()
    db.refresh(application)
    
    # Crear registro de auditoría
    audit = HHAuditLog(
        entity_type="application",
        entity_id=application_id,
        action="update",
        changed_by=current_user.get("email", "system"),
        diff_json={
            "contact_status": status_update.status,
            "stage": {"old": old_stage, "new": application.stage}
        }
    )
    db.add(audit)
    db.commit()
    
    return application


@router.post("/{application_id}/send-message")
def send_message_to_candidate(
    application_id: UUID,
    message_request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Enviar mensaje al candidato (email o whatsapp).
    Requiere que el candidato tenga datos de contacto.
    """
    application = db.query(HHApplication).options(
        joinedload(HHApplication.candidate)
    ).filter(HHApplication.application_id == application_id).first()
    
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
        db.commit()
    
    # Crear registro de auditoría
    audit = HHAuditLog(
        entity_type="application",
        entity_id=application_id,
        action="update",
        changed_by=current_user.get("email", "system"),
        diff_json={
            "message_sent": True,
            "channel": message_request.channel,
            "template_id": message_request.template_id
        }
    )
    db.add(audit)
    db.commit()
    
    return {
        "success": True,
        "message": f"Mensaje enviado exitosamente por {message_request.channel}",
        "candidate_id": str(candidate.candidate_id),
        "channel": message_request.channel
    }
