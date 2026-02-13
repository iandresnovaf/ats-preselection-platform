"""API endpoints para Candidatos."""
from typing import Optional
import uuid
import shutil
import os
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_consultant, require_viewer
from app.core.llm_rate_limit import get_llm_rate_limiter
from app.core.config import settings
from app.models import User, CandidateStatus
from app.schemas import (
    CandidateCreate,
    CandidateUpdate,
    CandidateResponse,
    CandidateWithEvaluation,
    CandidateListResponse,
    EvaluationResponse,
    ChangeStatusRequest,
    EvaluateRequest,
    MessageResponse,
)
from app.services import CandidateService, JobService, EvaluationService
from app.services.rhtools.document_processor import DocumentProcessor
from app.services.rhtools.resume_parser import ResumeParser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.get("", response_model=CandidateListResponse)
async def list_candidates(
    job_opening_id: Optional[str] = Query(None, description="Filtrar por oferta de trabajo"),
    status: Optional[str] = Query(None, description="Filtrar por estado del candidato"),
    source: Optional[str] = Query(None, description="Filtrar por fuente"),
    search: Optional[str] = Query(None, description="Buscar por nombre o email"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),  # VIEWER, CONSULTANT o ADMIN pueden ver
):
    """Listar candidatos con filtros y paginación."""
    candidate_service = CandidateService(db)
    
    skip = (page - 1) * page_size
    candidates, total = await candidate_service.list_candidates(
        job_opening_id=job_opening_id,
        status=status,
        source=source,
        search=search,
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


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    data: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Crear nuevo candidato (solo consultor o admin)."""
    candidate_service = CandidateService(db)
    job_service = JobService(db)
    
    # Verificar que la oferta existe
    job = await job_service.get_by_id(data.job_opening_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    candidate = await candidate_service.create_candidate(data)
    return candidate


@router.get("/{candidate_id}", response_model=CandidateWithEvaluation)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),  # VIEWER, CONSULTANT o ADMIN pueden ver
):
    """Obtener candidato por ID con sus evaluaciones."""
    candidate_service = CandidateService(db)
    evaluation_service = EvaluationService(db)
    
    candidate = await candidate_service.get_by_id_with_evaluations(candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidato no encontrado",
        )
    
    # Obtener evaluaciones
    evaluations = await evaluation_service.get_candidate_evaluations(candidate_id)
    
    # Obtener la evaluación más reciente
    latest = await evaluation_service.get_latest_evaluation(candidate_id)
    
    # Construir respuesta
    candidate_dict = {
        "id": str(candidate.id),
        "job_opening_id": str(candidate.job_opening_id),
        "email": candidate.email,
        "phone": candidate.phone,
        "full_name": candidate.full_name,
        "status": candidate.status,
        "zoho_candidate_id": candidate.zoho_candidate_id,
        "is_duplicate": candidate.is_duplicate,
        "duplicate_of_id": str(candidate.duplicate_of_id) if candidate.duplicate_of_id else None,
        "created_at": candidate.created_at,
        "updated_at": candidate.updated_at,
        "source": candidate.source,
        "evaluations": evaluations,
        "latest_score": latest.score if latest else None,
        "latest_decision": latest.decision if latest else None,
    }
    
    return candidate_dict


@router.patch("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    data: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Actualizar candidato (solo consultor o admin)."""
    candidate_service = CandidateService(db)
    
    candidate = await candidate_service.update_candidate(candidate_id, data)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidato no encontrado",
        )
    
    return candidate


@router.post("/{candidate_id}/evaluate", response_model=EvaluationResponse)
async def evaluate_candidate(
    request: Request,
    candidate_id: str,
    eval_request: EvaluateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """
    Evaluar candidato con LLM (solo consultor o admin).
    
    Rate Limits:
    - 5 requests por minuto por usuario
    - 50 requests por hora por usuario
    - 200 requests por día por usuario
    """
    # Rate limiting para LLM
    rate_limiter = get_llm_rate_limiter()
    
    # Obtener IP del cliente
    forwarded = request.headers.get("X-Forwarded-For")
    ip_address = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    
    user_id = str(current_user.id)
    
    # Verificar rate limit
    limits = await rate_limiter.check_rate_limit(user_id, ip_address)
    
    if not limits["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Has excedido el límite de {limits['violated']}. "
                           f"Intenta de nuevo en {limits['retry_after']} segundos.",
                "retry_after": limits["retry_after"],
                "limits": limits["limits"]
            },
            headers={"Retry-After": str(limits["retry_after"])}
        )
    
    candidate_service = CandidateService(db)
    job_service = JobService(db)
    evaluation_service = EvaluationService(db)
    
    # Verificar que el candidato existe
    candidate = await candidate_service.get_by_id(candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidato no encontrado",
        )
    
    # Obtener la oferta de trabajo
    job = await job_service.get_by_id(str(candidate.job_opening_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    # Verificar si ya tiene evaluación y no se fuerza re-evaluación
    if not eval_request.force:
        latest = await evaluation_service.get_latest_evaluation(candidate_id)
        if latest:
            # Agregar headers de rate limit a la respuesta
            response = latest
            response._rate_limit_headers = {
                "X-RateLimit-Limit": str(limits["limits"]["minute"]["limit"]),
                "X-RateLimit-Remaining": str(limits["limits"]["minute"]["remaining"]),
                "X-Cache": "HIT"
            }
            return response
    
    # Configuración del LLM
    llm_config = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "prompt_version": "v1.0",
    }
    
    try:
        evaluation = await candidate_service.evaluate_candidate(
            candidate_id=candidate_id,
            job_opening=job,
            llm_config=llm_config,
            force_refresh=eval_request.force,
        )
        
        # Agregar headers de rate limit (nota: FastAPI no permite modificar headers
        # directamente en la respuesta del modelo, pero se pueden agregar en middleware)
        
        return evaluation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{candidate_id}/change-status", response_model=CandidateResponse)
async def change_candidate_status(
    candidate_id: str,
    request: ChangeStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Cambiar estado del candidato (solo consultor o admin)."""
    candidate_service = CandidateService(db)
    
    # Validar estado
    valid_statuses = [s.value for s in CandidateStatus]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido. Estados válidos: {', '.join(valid_statuses)}",
        )
    
    candidate = await candidate_service.change_status(candidate_id, request.status)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidato no encontrado",
        )
    
    return candidate


@router.post("/upload-cv", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate_from_cv(
    cv_file: UploadFile = File(..., description="Archivo CV del candidato (PDF, DOCX, DOC)"),
    job_opening_id: str = Form(..., description="ID de la oferta de trabajo"),
    email: Optional[str] = Form(None, description="Email del candidato (opcional, se extrae del CV)"),
    phone: Optional[str] = Form(None, description="Teléfono del candidato (opcional, se extrae del CV)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Crear candidato subiendo un CV (PDF, DOCX, DOC).
    
    El sistema extraerá automáticamente:
    - Nombre completo
    - Email
    - Teléfono
    - Habilidades (skills)
    - Experiencia laboral
    - Educación
    """
    candidate_service = CandidateService(db)
    job_service = JobService(db)
    
    # Verificar que la oferta existe
    job = await job_service.get_by_id(job_opening_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    # Validar tipo de archivo
    allowed_types = {
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/msword': '.doc',
        'application/octet-stream': '.docx',  # A veces DOCX viene así
    }
    
    file_extension = allowed_types.get(cv_file.content_type)
    if not file_extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no soportado: {cv_file.content_type}. Use PDF, DOCX o DOC.",
        )
    
    # Validar tamaño (máximo 10MB)
    contents = await cv_file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archivo demasiado grande. Máximo 10MB.",
        )
    
    # Guardar archivo temporalmente
    temp_dir = os.path.join(settings.UPLOAD_DIR, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_filename = f"{uuid.uuid4()}{file_extension}"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    try:
        with open(temp_path, 'wb') as f:
            f.write(contents)
        
        # Procesar el documento con OCR
        processor = DocumentProcessor(db_session=db)
        
        # Detectar tipo MIME real
        detected_mime = processor.detect_mime_type(temp_path, cv_file.filename)
        
        if not processor.is_supported(detected_mime):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de archivo no soportado para extracción de texto.",
            )
        
        # Extraer texto del CV
        file_type = processor.get_file_type(detected_mime)
        extraction_result = await processor._extract_by_type(temp_path, file_type)
        extracted_text = extraction_result.get('text', '')
        
        if not extracted_text or len(extracted_text) < 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo extraer texto suficiente del CV. Verifique que el archivo no esté corrupto o protegido.",
            )
        
        # Parsear el CV con IA para extraer datos estructurados
        resume_parser = ResumeParser()
        
        # Usar el texto extraído para parsear (document_id temporal)
        parsed_result = await resume_parser.parse_resume(str(uuid.uuid4()), extracted_text)
        parsed_data = parsed_result.get('parsed_data', {})
        
        # Extraer datos del parseo
        full_name = parsed_data.get('full_name', '')
        extracted_email = parsed_data.get('email', '')
        extracted_phone = parsed_data.get('phone', '')
        skills = parsed_data.get('skills', [])
        experience_years = parsed_data.get('years_of_experience', 0)
        
        # Usar datos proporcionados o extraídos
        final_email = email or extracted_email
        final_phone = phone or extracted_phone
        
        if not final_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo extraer el email del CV. Por favor proporcione el email manualmente.",
            )
        
        # Crear el candidato
        candidate_data = CandidateCreate(
            email=final_email,
            phone=final_phone,
            full_name=full_name or "Candidato sin nombre",
            job_opening_id=job_opening_id,
            source='cv_upload',
            raw_data={
                'cv_extraction': parsed_data,
                'extraction_method': extraction_result.get('method', 'unknown'),
                'original_filename': cv_file.filename,
            },
            extracted_skills=skills,
            extracted_experience=experience_years,
            extracted_education=parsed_data.get('education', []),
        )
        
        candidate = await candidate_service.create_candidate(candidate_data)
        
        return candidate
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando CV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando el CV: {str(e)}",
        )
    finally:
        # Limpiar archivo temporal
        if os.path.exists(temp_path):
            os.remove(temp_path)
