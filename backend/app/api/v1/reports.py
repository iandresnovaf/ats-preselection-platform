"""
Core ATS API - Reports Router
Endpoints para reportes y análisis.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core_ats import (
    HHAuditLog,
    HHApplication, HHCandidate, HHRole, HHClient, HHAssessment, HHFlag,
    HHInterview, HHAssessmentScore
)
from app.schemas.core_ats import (
    TernaReportResponse, TernaCandidateComparison,
    RoleAnalyticsResponse, RoleAnalyticsMetrics,
    CandidateHistoryResponse, CandidateHistoryApplication
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/terna", response_model=TernaReportResponse)
def get_terna_report(
    role_id: UUID = Query(..., description="ID de la vacante"),
    candidate_ids: Optional[List[UUID]] = Query(None, description="IDs de candidatos a comparar (opcional)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Reporte de comparación de terna.
    Compara candidatos para una misma vacante.
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
            HHApplication.stage.in_(['terna', 'interview', 'offer', 'hired'])
        ).order_by(desc(HHApplication.overall_score).nullslast())
    
    applications = apps_query.limit(5).all()
    
    if not applications:
        raise HTTPException(status_code=404, detail="No se encontraron aplicaciones para comparar")
    
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


@router.get("/role-analytics/{role_id}", response_model=RoleAnalyticsResponse)
def get_role_analytics(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Análisis de métricas para una vacante específica.
    """
    role = db.query(HHRole).options(
        joinedload(HHRole.client)
    ).filter(HHRole.role_id == role_id).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    # Conteos por etapa
    stage_counts = db.query(
        HHApplication.stage,
        func.count(HHApplication.application_id).label('count')
    ).filter(HHApplication.role_id == role_id).group_by(HHApplication.stage).all()
    
    by_stage = {s.stage.value if hasattr(s.stage, 'value') else s.stage: s.count for s in stage_counts}
    
    # Conteos generales
    total = sum(by_stage.values())
    hired_count = by_stage.get('hired', 0)
    rejected_count = by_stage.get('rejected', 0)
    
    # Score promedio
    avg_score = db.query(func.avg(HHApplication.overall_score)).filter(
        HHApplication.role_id == role_id,
        HHApplication.overall_score.isnot(None)
    ).scalar()
    
    # Tiempo promedio de contratación (días desde sourcing a hired)
    hired_apps = db.query(HHApplication).filter(
        HHApplication.role_id == role_id,
        HHApplication.hired == True,
        HHApplication.decision_date.isnot(None)
    ).all()
    
    avg_days = None
    if hired_apps:
        total_days = 0
        valid_count = 0
        for app in hired_apps:
            if app.decision_date and app.created_at:
                days = (app.decision_date - app.created_at.date()).days
                if days >= 0:
                    total_days += days
                    valid_count += 1
        if valid_count > 0:
            avg_days = total_days // valid_count
    
    metrics = RoleAnalyticsMetrics(
        total_applications=total,
        by_stage=by_stage,
        hired_count=hired_count,
        rejected_count=rejected_count,
        avg_overall_score=avg_score,
        avg_time_to_hire_days=avg_days
    )
    
    return RoleAnalyticsResponse(
        role_id=role_id,
        role_title=role.role_title,
        metrics=metrics
    )


@router.get("/candidate-history/{candidate_id}", response_model=CandidateHistoryResponse)
def get_candidate_history(
    candidate_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Historial completo de aplicaciones de un candidato.
    """
    candidate = db.query(HHCandidate).filter(HHCandidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    applications = db.query(HHApplication).options(
        joinedload(HHApplication.role).joinedload(HHRole.client)
    ).filter(HHApplication.candidate_id == candidate_id).order_by(desc(HHApplication.created_at)).all()
    
    applications_data = []
    for app in applications:
        role = app.role
        client = role.client if role else None
        
        applications_data.append(CandidateHistoryApplication(
            application_id=app.application_id,
            role_title=role.role_title if role else "N/A",
            client_name=client.client_name if client else "N/A",
            stage=app.stage.value if hasattr(app.stage, 'value') else app.stage,
            hired=app.hired,
            decision_date=app.decision_date,
            overall_score=app.overall_score,
            created_at=app.created_at
        ))
    
    hired_count = sum(1 for a in applications if a.hired)
    
    return CandidateHistoryResponse(
        candidate_id=candidate_id,
        full_name=candidate.full_name,
        total_applications=len(applications),
        hired_count=hired_count,
        applications=applications_data
    )
