"""API endpoints para el pipeline de procesamiento de documentos."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_viewer, require_consultant
from app.models import User
from app.models.rhtools import Document, DocumentTextExtraction
from app.pipeline.document_pipeline import DocumentPipeline, PipelineError
from app.services.extraction.models import (
    ProcessingStatus, PipelineJob, ExtractionResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["document-pipeline"])


class ProcessDocumentResponse:
    """Respuesta de procesamiento de documento."""
    def __init__(self, job_id: str, document_id: str, status: str, message: str):
        self.job_id = job_id
        self.document_id = document_id
        self.status = status
        self.message = message


@router.post("/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
async def process_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant)
):
    """Inicia el pipeline de procesamiento de un documento.
    
    Estados: uploaded → parsing → extracting → validating → completed/error
    
    Args:
        document_id: ID del documento a procesar
        
    Returns:
        Job ID para tracking del procesamiento
    """
    # Verificar que el documento existe
    result = await db.execute(
        select(Document).where(Document.id == UUID(document_id))
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    # Iniciar pipeline
    pipeline = DocumentPipeline(db_session=db)
    
    try:
        job = await pipeline.process(document_id)
        
        return {
            "job_id": job.job_id,
            "document_id": document_id,
            "status": job.status.value,
            "message": f"Procesamiento iniciado. Estado actual: {job.status.value}",
            "started_at": job.started_at.isoformat() if job.started_at else None,
        }
        
    except PipelineError as e:
        logger.error(f"Error iniciando pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer)
):
    """Obtiene el estado actual del procesamiento de un documento.
    
    Estados posibles:
    - uploaded: Documento subido, pendiente de procesar
    - parsing: Extrayendo texto del documento
    - extracting: Extrayendo datos estructurados
    - validating: Validando datos extraídos
    - completed: Procesamiento completado exitosamente
    - error: Error en el procesamiento
    - manual_review: Esperando revisión manual
    - confirmed: Datos confirmados manualmente
    
    Args:
        document_id: ID del documento
        
    Returns:
        Estado actual y metadatos
    """
    # Obtener documento
    result = await db.execute(
        select(Document).where(Document.id == UUID(document_id))
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    # Obtener extracción si existe
    extraction_result = await db.execute(
        select(DocumentTextExtraction).where(
            DocumentTextExtraction.document_id == UUID(document_id)
        )
    )
    extraction = extraction_result.scalar_one_or_none()
    
    # Mapear estado
    status_map = {
        'pending': 'uploaded',
        'processing': 'parsing',
        'processed': 'completed',
        'error': 'error',
    }
    
    current_status = status_map.get(document.status, document.status)
    
    response = {
        "document_id": document_id,
        "status": current_status,
        "document_type": document.document_type,
        "original_filename": document.original_filename,
        "mime_type": document.mime_type,
        "file_size": document.file_size,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
    }
    
    # Agregar información de extracción si existe
    if extraction:
        response["extraction"] = {
            "status": extraction.status,
            "extraction_engine": extraction.extraction_engine,
            "text_length": len(extraction.extracted_text) if extraction.extracted_text else 0,
            "processed_at": extraction.processed_at.isoformat() if extraction.processed_at else None,
        }
        
        # Agregar datos parseados si existen
        if extraction.parsed_data:
            response["extraction"]["parsed_data"] = {
                "document_type": extraction.parsed_data.get("document_type"),
                "confidence": extraction.parsed_data.get("confidence"),
                "has_data": extraction.parsed_data.get("data") is not None,
                "validation_valid": extraction.parsed_data.get("validation", {}).get("is_valid"),
                "manual_confirmation": extraction.parsed_data.get("manual_confirmation", False),
            }
    
    return response


@router.post("/{document_id}/extract/confirm")
async def confirm_extraction(
    document_id: str,
    confirmed_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant)
):
    """Confirma o corrige datos extraídos manualmente (modo asistido).
    
    Este endpoint permite a los usuarios revisar y confirmar los datos
    extraídos automáticamente antes de guardarlos definitivamente.
    
    Args:
        document_id: ID del documento
        confirmed_data: Datos confirmados/corregidos por el usuario
        
    Returns:
        Resultado de la confirmación
    """
    # Verificar que el documento existe
    result = await db.execute(
        select(Document).where(Document.id == UUID(document_id))
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    # Verificar que existe una extracción previa
    extraction_result = await db.execute(
        select(DocumentTextExtraction).where(
            DocumentTextExtraction.document_id == UUID(document_id)
        )
    )
    extraction = extraction_result.scalar_one_or_none()
    
    if not extraction:
        raise HTTPException(
            status_code=400, 
            detail="No existe extracción previa. Procese el documento primero."
        )
    
    # Procesar confirmación manual
    pipeline = DocumentPipeline(db_session=db)
    
    try:
        job = await pipeline.process_manual_review(document_id, confirmed_data)
        
        return {
            "job_id": job.job_id,
            "document_id": document_id,
            "status": job.status.value,
            "message": "Datos confirmados y guardados exitosamente",
            "confirmed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
        
    except Exception as e:
        logger.error(f"Error confirmando extracción: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/extract")
async def get_extraction(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer)
):
    """Obtiene los datos extraídos de un documento para revisión.
    
    Args:
        document_id: ID del documento
        
    Returns:
        Datos extraídos con confianza y advertencias
    """
    result = await db.execute(
        select(DocumentTextExtraction).where(
            DocumentTextExtraction.document_id == UUID(document_id)
        )
    )
    extraction = result.scalar_one_or_none()
    
    if not extraction:
        raise HTTPException(status_code=404, detail="Extracción no encontrada")
    
    if not extraction.parsed_data:
        raise HTTPException(
            status_code=400, 
            detail="Documento aún no ha sido procesado completamente"
        )
    
    return {
        "document_id": document_id,
        "document_type": extraction.parsed_data.get("document_type"),
        "confidence": extraction.parsed_data.get("confidence"),
        "data": extraction.parsed_data.get("data"),
        "normalized_data": extraction.parsed_data.get("normalized_data"),
        "validation": extraction.parsed_data.get("validation"),
        "manual_confirmation": extraction.parsed_data.get("manual_confirmation", False),
        "extracted_at": extraction.processed_at.isoformat() if extraction.processed_at else None,
    }


@router.get("/{document_id}/extract/preview")
async def preview_extraction(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_consultant)
):
    """Genera una vista previa de la extracción sin guardar (dry-run).
    
    Útil para previsualizar cómo se extraerán los datos antes de procesar.
    
    Args:
        document_id: ID del documento
        
    Returns:
        Vista previa de la extracción
    """
    from app.services.extraction.document_parser import DocumentParser
    from app.services.extraction.assessment_extractor import AssessmentExtractor
    from app.services.extraction.cv_extractor import CVExtractor
    from app.services.extraction.interview_extractor import InterviewExtractor
    
    # Obtener documento
    result = await db.execute(
        select(Document).where(Document.id == UUID(document_id))
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    # Parsear documento
    parser = DocumentParser()
    
    try:
        parse_result = await parser.parse_document(
            document_id=document_id,
            file_path=document.file_path,
            mime_type=document.mime_type
        )
        
        if parse_result.status == ProcessingStatus.ERROR:
            raise HTTPException(
                status_code=500, 
                detail=f"Error en parsing: {parse_result.error_message}"
            )
        
        # Extraer datos según tipo detectado
        doc_type = parse_result.document_type
        
        if doc_type.value == "assessment":
            extractor = AssessmentExtractor()
            data = await extractor.extract_from_text(parse_result.text)
            preview_data = data.dict()
        elif doc_type.value == "cv":
            extractor = CVExtractor()
            data = await extractor.extract_from_text(parse_result.text)
            preview_data = data.dict()
        elif doc_type.value == "interview":
            extractor = InterviewExtractor()
            data = await extractor.extract_from_text(parse_result.text)
            preview_data = data.dict()
        else:
            preview_data = {
                "detected_type": doc_type.value,
                "text_preview": parse_result.text[:500] if parse_result.text else None,
                "message": "Tipo de documento no soportado para extracción automática"
            }
        
        return {
            "document_id": document_id,
            "detected_type": doc_type.value,
            "text_length": len(parse_result.text) if parse_result.text else 0,
            "preview": preview_data,
            "metadata": parse_result.metadata,
        }
        
    except Exception as e:
        logger.error(f"Error generando preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
