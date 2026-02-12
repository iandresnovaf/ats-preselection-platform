"""API endpoints para el módulo RHTools - Documentos y Parsing de CVs."""
import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_viewer, require_consultant
from app.models import User
from app.models.rhtools import Document, DocumentTextExtraction, ResumeParse, DocumentType, DocumentStatus
from app.schemas.rhtools import (
    DocumentResponse, DocumentListResponse, DocumentUploadResponse,
    DocumentTextExtractionResponse, ResumeParseResponse, ResumeParseRequest,
    ResumeParseUpdate, ValidationResult
)
from app.services.rhtools import DocumentProcessor, ResumeParser
from app.tasks.rhtools import process_document_async, parse_resume_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.jpg', '.jpeg', '.png', '.tiff'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def get_file_extension(filename: str) -> str:
    """Obtiene la extensión del archivo."""
    return os.path.splitext(filename)[1].lower()


def is_allowed_file(filename: str) -> bool:
    """Verifica si el tipo de archivo está permitido."""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    candidate_id: Optional[str] = Form(None),
    doc_type: str = Form("cv"),
    background_processing: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant)  # Solo CONSULTANT o ADMIN pueden subir
):
    """Sube un documento (CV, certificado, etc.).
    
    Args:
        file: Archivo a subir
        candidate_id: ID del candidato asociado (opcional)
        doc_type: Tipo de documento (cv, resume, cover_letter, etc.)
        background_processing: Procesar en background con Celery
    """
    # Validar archivo
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Leer contenido
    contents = await file.read()
    
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Generar nombre único
    file_ext = get_file_extension(file.filename)
    stored_filename = f"{uuid.uuid4()}{file_ext}"
    
    # Guardar archivo
    upload_dir = os.environ.get("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, stored_filename)
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Crear registro en BD
    document = Document(
        candidate_id=uuid.UUID(candidate_id) if candidate_id else None,
        original_filename=file.filename,
        stored_filename=stored_filename,
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(contents),
        doc_type=doc_type if doc_type in [t.value for t in DocumentType] else "other",
        status=DocumentStatus.PENDING.value
    )
    
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    logger.info(f"Document uploaded: {document.id} - {file.filename}")
    
    # Encolar para procesamiento
    if background_processing:
        task = process_document_async.delay(str(document.id))
        logger.info(f"Queued document {document.id} for processing, task: {task.id}")
    
    return DocumentUploadResponse(
        id=str(document.id),
        message="Document uploaded successfully. Processing in background.",
        status="pending"
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    candidate_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer)  # VIEWER, CONSULTANT o ADMIN pueden ver
):
    """Lista documentos con filtros opcionales."""
    # Construir query
    query = select(Document)
    
    if candidate_id:
        query = query.where(Document.candidate_id == uuid.UUID(candidate_id))
    
    if doc_type:
        query = query.where(Document.doc_type == doc_type)
    
    if status:
        query = query.where(Document.status == status)
    
    # Contar total
    count_query = select(Document).select_from(Document)
    if candidate_id:
        count_query = count_query.where(Document.candidate_id == uuid.UUID(candidate_id))
    if doc_type:
        count_query = count_query.where(Document.doc_type == doc_type)
    if status:
        count_query = count_query.where(Document.status == status)
    
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())
    
    # Paginar
    offset = (page - 1) * page_size
    query = query.order_by(desc(Document.created_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
        has_next=page * page_size < total,
        has_prev=page > 1
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer)  # VIEWER, CONSULTANT o ADMIN pueden ver
):
    """Obtiene un documento por ID."""
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant)  # Solo CONSULTANT o ADMIN pueden eliminar
):
    """Elimina un documento."""
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Eliminar archivo físico
    upload_dir = os.environ.get("UPLOAD_DIR", "./uploads")
    file_path = os.path.join(upload_dir, document.stored_filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Eliminar de BD
    await db.delete(document)
    await db.commit()
    
    logger.info(f"Document deleted: {document_id}")
    
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={})


@router.get("/{document_id}/text", response_model=DocumentTextExtractionResponse)
async def get_document_text(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer)  # VIEWER, CONSULTANT o ADMIN pueden ver
):
    """Obtiene el texto extraído de un documento."""
    result = await db.execute(
        select(DocumentTextExtraction).where(
            DocumentTextExtraction.document_id == uuid.UUID(document_id)
        )
    )
    extraction = result.scalar_one_or_none()
    
    if not extraction:
        raise HTTPException(status_code=404, detail="Text extraction not found")
    
    return DocumentTextExtractionResponse.model_validate(extraction)


@router.post("/{document_id}/extract", response_model=DocumentTextExtractionResponse)
async def extract_document_text(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant)  # Solo CONSULTANT o ADMIN pueden extraer
):
    """Extrae texto de un documento (síncrono)."""
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    processor = DocumentProcessor(db_session=db)
    
    try:
        extraction = await processor.extract_text(document_id)
        return DocumentTextExtractionResponse.model_validate(extraction)
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.get("/{document_id}/parse", response_model=ResumeParseResponse)
async def get_resume_parse(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer)  # VIEWER, CONSULTANT o ADMIN pueden ver
):
    """Obtiene el resultado del parsing de un CV."""
    result = await db.execute(
        select(ResumeParse).where(ResumeParse.document_id == uuid.UUID(document_id))
    )
    parse = result.scalar_one_or_none()
    
    if not parse:
        raise HTTPException(status_code=404, detail="Resume parse not found")
    
    return ResumeParseResponse.model_validate(parse)


@router.post("/{document_id}/parse", response_model=ResumeParseResponse)
async def parse_resume(
    document_id: str,
    request: ResumeParseRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant)  # Solo CONSULTANT o ADMIN pueden parsear
):
    """Parsea un CV con IA (síncrono)."""
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Verificar que tiene texto extraído
    if not document.text_extraction:
        raise HTTPException(
            status_code=400, 
            detail="Document has no extracted text. Run extraction first."
        )
    
    parser = ResumeParser(db_session=db)
    
    try:
        parse_result = await parser.parse_and_save(document_id)
        return ResumeParseResponse.model_validate(parse_result)
    except Exception as e:
        logger.error(f"Error parsing resume: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@router.post("/{document_id}/reparse", response_model=ResumeParseResponse)
async def reparse_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant)  # Solo CONSULTANT o ADMIN pueden reparsear
):
    """Forzar re-parseo manual de un CV (usar cuando el recruiter corrige datos).
    
    Este endpoint encola una tarea de Celery para re-parsear el documento.
    """
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Encolar tarea de re-parseo
    task = parse_resume_async.delay(document_id, force=True)
    
    logger.info(f"Queued re-parse for document {document_id}, task: {task.id}")
    
    # Retornar el parseo existente mientras se procesa
    result = await db.execute(
        select(ResumeParse).where(ResumeParse.document_id == uuid.UUID(document_id))
    )
    existing_parse = result.scalar_one_or_none()
    
    if existing_parse:
        return ResumeParseResponse.model_validate(existing_parse)
    
    # Si no existe, retornar respuesta de pending
    raise HTTPException(
        status_code=202, 
        detail=f"Re-parse queued. Task ID: {task.id}"
    )


@router.put("/{document_id}/parse", response_model=ResumeParseResponse)
async def update_parsed_data(
    document_id: str,
    update: ResumeParseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant)  # Solo CONSULTANT o ADMIN pueden actualizar
):
    """Actualiza datos parseados manualmente (corrección por recruiter).
    
    Permite a un recruiter corregir los datos extraídos por la IA.
    """
    parser = ResumeParser(db_session=db)
    
    try:
        parse_result = await parser.reparse_document(
            document_id, 
            corrected_data=update.parsed_data.model_dump()
        )
        return ResumeParseResponse.model_validate(parse_result)
    except Exception as e:
        logger.error(f"Error updating parsed data: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@router.get("/{document_id}/validate", response_model=ValidationResult)
async def validate_parsed_data(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer)  # VIEWER, CONSULTANT o ADMIN pueden ver
):
    """Valida los datos parseados de un CV y retorna score de confianza."""
    result = await db.execute(
        select(ResumeParse).where(ResumeParse.document_id == uuid.UUID(document_id))
    )
    parse = result.scalar_one_or_none()
    
    if not parse or not parse.parsed_data:
        raise HTTPException(status_code=404, detail="Resume parse not found")
    
    parser = ResumeParser(db_session=db)
    confidence_score, breakdown = parser.calculate_confidence_score(parse.parsed_data)
    
    # Generar warnings/sugerencias
    warnings = []
    errors = []
    suggestions = []
    
    data = parse.parsed_data
    
    if not data.get('name') or data['name'] == 'Unknown':
        errors.append("Name not detected")
    
    if not data.get('email'):
        errors.append("Email not detected")
    
    if not data.get('experience'):
        warnings.append("No work experience found")
    
    if not data.get('education'):
        warnings.append("No education found")
    
    if not data.get('skills'):
        suggestions.append("Consider adding skills manually")
    
    if breakdown.get('dates_format', 0) < 0.5:
        warnings.append("Some dates have unusual format")
    
    return ValidationResult(
        is_valid=len(errors) == 0 and confidence_score > 0.5,
        confidence=breakdown,
        warnings=warnings,
        errors=errors,
        suggestions=suggestions
    )
