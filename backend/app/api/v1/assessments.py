"""
Core ATS API - Assessments Router
Endpoints para gestión de evaluaciones psicométricas y sus scores dinámicos.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core_ats import Assessment, AssessmentScore, Application, Document
from app.schemas.core_ats import (
    AssessmentCreate, AssessmentUpdate, AssessmentResponse,
    AssessmentWithScoresResponse, AssessmentScoreCreate,
    AssessmentScoreBatchCreate, AssessmentScoreResponse
)

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(
    assessment: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crear una nueva evaluación psicométrica."""
    # Verificar que la aplicación existe
    application = db.query(Application).filter(
        Application.application_id == assessment.application_id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    # Verificar que el documento existe si se proporciona
    if assessment.raw_pdf_id:
        doc = db.query(Document).filter(Document.document_id == assessment.raw_pdf_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    assessment_data = assessment.model_dump()
    db_assessment = Assessment(**assessment_data)
    db.add(db_assessment)
    db.commit()
    db.refresh(db_assessment)
    
    return db_assessment


@router.get("/{assessment_id}", response_model=AssessmentWithScoresResponse)
def get_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener una evaluación con todos sus scores."""
    assessment = db.query(Assessment).options(
        joinedload(Assessment.scores),
        joinedload(Assessment.raw_document)
    ).filter(Assessment.assessment_id == assessment_id).first()
    
    if not assessment:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
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
    
    return AssessmentWithScoresResponse(
        assessment_id=assessment.assessment_id,
        application_id=assessment.application_id,
        assessment_type=assessment.assessment_type.value if hasattr(assessment.assessment_type, 'value') else assessment.assessment_type,
        assessment_date=assessment.assessment_date,
        sincerity_score=assessment.sincerity_score,
        raw_pdf_id=assessment.raw_pdf_id,
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
        scores=scores_data
    )


@router.post("/{assessment_id}/scores", response_model=List[AssessmentScoreResponse], status_code=status.HTTP_201_CREATED)
def create_assessment_scores(
    assessment_id: UUID,
    scores_data: AssessmentScoreBatchCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Crear múltiples scores para una evaluación (batch insert).
    Este diseño dinámico permite guardar cualquier dimensión sin cambiar el schema.
    """
    # Verificar que la evaluación existe
    assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    created_scores = []
    for score_create in scores_data.scores:
        # Validar rango 0-100
        if score_create.value < 0 or score_create.value > 100:
            raise HTTPException(
                status_code=400,
                detail=f"El valor {score_create.value} está fuera del rango 0-100"
            )
        
        db_score = AssessmentScore(
            assessment_id=assessment_id,
            dimension=score_create.dimension,
            value=score_create.value,
            unit=score_create.unit,
            source_page=score_create.source_page
        )
        db.add(db_score)
        created_scores.append(db_score)
    
    db.commit()
    for score in created_scores:
        db.refresh(score)
    
    return [
        AssessmentScoreResponse(
            score_id=s.score_id,
            assessment_id=s.assessment_id,
            dimension=s.dimension,
            value=s.value,
            unit=s.unit,
            source_page=s.source_page,
            created_at=s.created_at
        ) for s in created_scores
    ]


@router.get("/{assessment_id}/scores", response_model=List[AssessmentScoreResponse])
def get_assessment_scores(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener todos los scores de una evaluación."""
    assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    scores = db.query(AssessmentScore).filter(
        AssessmentScore.assessment_id == assessment_id
    ).all()
    
    return [
        AssessmentScoreResponse(
            score_id=s.score_id,
            assessment_id=s.assessment_id,
            dimension=s.dimension,
            value=s.value,
            unit=s.unit,
            source_page=s.source_page,
            created_at=s.created_at
        ) for s in scores
    ]
