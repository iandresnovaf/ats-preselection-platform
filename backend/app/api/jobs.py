"""API endpoints para Ofertas de Trabajo (Jobs)."""
import os
import uuid as uuid_lib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_consultant, require_viewer
from app.models import User
from app.schemas import (
    JobOpeningCreate, 
    JobOpeningUpdate, 
    JobOpeningResponse,
    JobListResponse,
    CandidateListResponse,
    MessageResponse,
)
from app.services import JobService
from app.tasks.rhtools import process_document_async

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# Configuración para uploads
ALLOWED_JD_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}
MAX_JD_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def get_file_extension(filename: str) -> str:
    """Obtiene la extensión del archivo."""
    return os.path.splitext(filename)[1].lower()


def is_allowed_jd_file(filename: str) -> bool:
    """Verifica si el tipo de archivo está permitido para JD."""
    return get_file_extension(filename) in ALLOWED_JD_EXTENSIONS


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filtrar por estado (draft, active, closed, paused)"),
    assigned_consultant_id: Optional[str] = Query(None, description="Filtrar por consultor asignado"),
    search: Optional[str] = Query(None, description="Buscar por título, departamento o ubicación"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),  # VIEWER, CONSULTANT o ADMIN pueden ver
):
    """Listar ofertas de trabajo con filtros y paginación."""
    job_service = JobService(db)
    
    skip = (page - 1) * page_size
    jobs, total = await job_service.list_jobs(
        status=status,
        assigned_consultant_id=assigned_consultant_id,
        search=search,
        skip=skip,
        limit=page_size,
    )
    
    pages = (total + page_size - 1) // page_size
    
    return {
        "items": jobs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }


@router.post("", response_model=JobOpeningResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    data: JobOpeningCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Crear nueva oferta de trabajo (solo consultor o admin)."""
    job_service = JobService(db)
    
    job = await job_service.create_job(data)
    return job


@router.get("/{job_id}", response_model=JobOpeningResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),  # VIEWER, CONSULTANT o ADMIN pueden ver
):
    """Obtener oferta de trabajo por ID."""
    job_service = JobService(db)
    
    job = await job_service.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    return job


@router.patch("/{job_id}", response_model=JobOpeningResponse)
async def update_job(
    job_id: str,
    data: JobOpeningUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Actualizar oferta de trabajo (solo consultor o admin)."""
    job_service = JobService(db)
    
    job = await job_service.update_job(job_id, data)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Eliminar oferta de trabajo (solo consultor o admin)."""
    job_service = JobService(db)
    
    success = await job_service.delete_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    return None


@router.post("/{job_id}/close", response_model=JobOpeningResponse)
async def close_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """Cerrar oferta de trabajo (solo consultor o admin)."""
    job_service = JobService(db)
    
    job = await job_service.close_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    return job


@router.get("/{job_id}/candidates", response_model=CandidateListResponse)
async def get_job_candidates(
    job_id: str,
    status: Optional[str] = Query(None, description="Filtrar por estado del candidato"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),  # VIEWER, CONSULTANT o ADMIN pueden ver
):
    """Obtener candidatos de una oferta de trabajo."""
    job_service = JobService(db)
    
    # Verificar que la oferta existe
    job = await job_service.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    skip = (page - 1) * page_size
    candidates, total = await job_service.get_job_candidates(
        job_id=job_id,
        status=status,
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


@router.post("/{job_id}/upload-description", response_model=MessageResponse)
async def upload_job_description(
    job_id: str,
    file: UploadFile = File(..., description="Archivo PDF/Word del Job Description"),
    background_processing: bool = Form(default=True, description="Procesar en background"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant),
):
    """
    Sube un documento PDF/Word como Job Description para una oferta.
    
    - Requiere permisos de consultor o admin
    - Archivos permitidos: PDF, DOCX, DOC, TXT
    - Tamaño máximo: 10MB
    - El texto extraído se usará para matching con IA
    
    Args:
        job_id: ID del job
        file: Archivo del Job Description
        background_processing: Procesar extracción de texto en background
    
    Returns:
        Mensaje de confirmación con ID del documento
    """
    from app.models.rhtools import Document, DocumentType, DocumentStatus
    
    job_service = JobService(db)
    
    # Verificar que el job existe
    job = await job_service.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta de trabajo no encontrada",
        )
    
    # Validar permisos sobre el job
    if current_user.role != "super_admin":
        if str(job.assigned_consultant_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para modificar este job",
            )
    
    # Validar archivo
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se proporcionó archivo"
        )
    
    if not is_allowed_jd_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido. Permitidos: {', '.join(ALLOWED_JD_EXTENSIONS)}"
        )
    
    # Leer contenido
    contents = await file.read()
    
    if len(contents) > MAX_JD_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Archivo demasiado grande. Máximo: {MAX_JD_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Generar nombre único
    file_ext = get_file_extension(file.filename)
    stored_filename = f"jd_{uuid_lib.uuid4()}{file_ext}"
    
    # Guardar archivo
    upload_dir = os.environ.get("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, stored_filename)
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Crear documento en BD (sin candidate_id, es un JD de job)
    document = Document(
        candidate_id=None,  # No está asociado a un candidato
        original_filename=file.filename,
        storage_filename=stored_filename,  # Usar el nombre correcto del campo
        file_path=file_path,
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(contents),
        document_type=DocumentType.OTHER.value,  # Job Description
        document_category="job_description",  # Categoría especial para JD
        status=DocumentStatus.PENDING.value,
        uploaded_by=current_user.id,
    )
    
    db.add(document)
    await db.flush()
    await db.refresh(document)
    
    # Asociar documento al job
    job.job_description_file_id = document.id
    await db.flush()
    
    # Encolar para procesamiento de extracción de texto
    if background_processing:
        # Importar aquí para evitar circular imports
        from app.tasks.cv_processing import process_cv_async
        process_document_async.delay(str(document.id))
    
    return MessageResponse(
        message=f"Job Description subido correctamente. Documento ID: {document.id}",
        success=True
    )
