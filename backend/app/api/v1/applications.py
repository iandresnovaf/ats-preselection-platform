"""
Core ATS API - Applications Router
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
    Application, Candidate, Role, Client, Interview, Assessment,
    Flag, Document, AuditLog
)
from app.schemas.core_ats import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse,
    ApplicationListResponse, ApplicationWithDetailsResponse,
    ApplicationStageUpdate, ApplicationDecisionUpdate,
    ApplicationTimelineResponse, ApplicationTimelineEvent,
    ApplicationScoresSummary, ApplicationFlagsSummary,
    AssessmentWithScoresResponse, AssessmentScoreResponse,
    FlagResponse, CandidateResponse, RoleWithClientResponse,
    ClientResponse
)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    application: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crear una nueva aplicación (Candidato ↔ Vacante)."""
    # Verificar que el candidato existe
    candidate = db.query(Candidate).filter(Candidate.candidate_id == application.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    # Verificar que el rol existe
    role = db.query(Role).filter(Role.role_id == application.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    # Verificar que no exista ya una aplicación para este par
    existing = db.query(Application).filter(
        Application.candidate_id == application.candidate_id,
        Application.role_id == application.role_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una aplicación para este candidato en esta vacante"
        )
    
    app_data = application.model_dump()
    db_application = Application(**app_data)
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    
    # Crear registro de auditoría
    audit = AuditLog(
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
    query = db.query(Application)
    
    if role_id:
        query = query.filter(Application.role_id == role_id)
    if candidate_id:
        query = query.filter(Application.candidate_id == candidate_id)
    if stage:
        query = query.filter(Application.stage == stage)
    if hired is not None:
        query = query.filter(Application.hired == hired)
    
    total = query.count()
    applications = query.order_by(desc(Application.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
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
    application = db.query(Application).options(
        joinedload(Application.candidate),
        joinedload(Application.role).joinedload(Role.client),
        joinedload(Application.interviews),
        joinedload(Application.assessments),
        joinedload(Application.flags)
    ).filter(Application.application_id == application_id).first()
    
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
    application = db.query(Application).filter(Application.application_id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    old_stage = application.stage
    application.stage = stage_update.stage
    
    if stage_update.notes:
        application.notes = stage_update.notes
    
    db.commit()
    db.refresh(application)
    
    # Crear registro de auditoría
    audit = AuditLog(
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
    application = db.query(Application).filter(Application.application_id == application_id).first()
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
    audit = AuditLog(
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
    application = db.query(Application).filter(Application.application_id == application_id).first()
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
    
    # Eventos: Interviews
    for interview in application.interviews:
        events.append(ApplicationTimelineEvent(
            event_type="interview",
            event_date=interview.interview_date or interview.created_at,
            description=f"Entrevista con {interview.interviewer or 'N/A'}",
            metadata={"interviewer": interview.interviewer}
        ))
    
    # Eventos: Assessments
    for assessment in application.assessments:
        events.append(ApplicationTimelineEvent(
            event_type="assessment",
            event_date=datetime.combine(assessment.assessment_date, datetime.min.time()) if assessment.assessment_date else assessment.created_at,
            description=f"Evaluación: {assessment.assessment_type.value if hasattr(assessment.assessment_type, 'value') else assessment.assessment_type}",
            metadata={"assessment_type": assessment.assessment_type.value if hasattr(assessment.assessment_type, 'value') else assessment.assessment_type}
        ))
    
    # Eventos: Flags
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
    application = db.query(Application).options(
        joinedload(Application.assessments).joinedload(Assessment.scores)
    ).filter(Application.application_id == application_id).first()
    
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
    application = db.query(Application).options(
        joinedload(Application.flags)
    ).filter(Application.application_id == application_id).first()
    
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
