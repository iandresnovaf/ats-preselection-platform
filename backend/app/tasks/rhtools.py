"""Tareas Celery para el módulo RHTools - Procesamiento de CVs."""
import logging
from typing import Optional

from celery import chain

from app.tasks import celery_app
from app.core.database import async_session_maker
from app.models.rhtools import Document, DocumentStatus

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_document_async(self, document_id: str):
    """Extrae texto de un documento y lo parsea si es CV.
    
    Args:
        document_id: ID del documento a procesar
    """
    import asyncio
    
    async def _process():
        from app.services.rhtools import DocumentProcessor, ResumeParser
        
        async with async_session_maker() as db:
            try:
                # Extraer texto
                logger.info(f"Starting text extraction for document {document_id}")
                processor = DocumentProcessor(db_session=db)
                extraction = await processor.extract_text(document_id)
                
                logger.info(
                    f"Text extracted: {extraction.text_length} chars "
                    f"using {extraction.extraction_method}"
                )
                
                # Obtener documento para verificar tipo
                from sqlalchemy import select
                result = await db.execute(
                    select(Document).where(Document.id == document_id)
                )
                doc = result.scalar_one_or_none()
                
                if doc and doc.doc_type in ['cv', 'resume']:
                    # Es un CV, hacer parsing
                    logger.info(f"Document {document_id} is CV, starting parse")
                    parser = ResumeParser(db_session=db)
                    parse_result = await parser.parse_and_save(document_id)
                    
                    logger.info(
                        f"Resume parsed with confidence {parse_result.confidence_score}"
                    )
                    
                    return {
                        "status": "completed",
                        "document_id": document_id,
                        "text_length": extraction.text_length,
                        "confidence": parse_result.confidence_score,
                        "parse_status": parse_result.status
                    }
                
                return {
                    "status": "extracted_only",
                    "document_id": document_id,
                    "text_length": extraction.text_length
                }
                
            except Exception as e:
                logger.error(f"Error processing document {document_id}: {e}")
                await db.rollback()
                raise
    
    try:
        return asyncio.run(_process())
    except Exception as exc:
        logger.error(f"Task failed for document {document_id}: {exc}")
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def parse_resume_async(self, document_id: str, force: bool = False):
    """Parsea un CV con IA.
    
    Args:
        document_id: ID del documento a parsear
        force: Forzar re-parseo aunque ya exista
    """
    import asyncio
    
    async def _parse():
        from app.services.rhtools import ResumeParser
        from sqlalchemy import select
        
        async with async_session_maker() as db:
            try:
                # Verificar si ya existe parseo
                if not force:
                    from app.models.rhtools import ResumeParse
                    result = await db.execute(
                        select(ResumeParse).where(ResumeParse.document_id == document_id)
                    )
                    existing = result.scalar_one_or_none()
                    
                    if existing and existing.status == 'success':
                        logger.info(f"Parse already exists for {document_id}, skipping")
                        return {
                            "status": "skipped",
                            "document_id": document_id,
                            "reason": "already_parsed"
                        }
                
                # Parsear
                logger.info(f"Starting resume parsing for document {document_id}")
                parser = ResumeParser(db_session=db)
                parse_result = await parser.parse_and_save(document_id)
                
                return {
                    "status": "completed",
                    "document_id": document_id,
                    "confidence": parse_result.confidence_score,
                    "parse_status": parse_result.status,
                    "tokens_used": parse_result.total_tokens,
                    "cost_usd": parse_result.estimated_cost_usd
                }
                
            except Exception as e:
                logger.error(f"Error parsing resume {document_id}: {e}")
                await db.rollback()
                raise
    
    try:
        return asyncio.run(_parse())
    except Exception as exc:
        logger.error(f"Parse task failed for document {document_id}: {exc}")
        self.retry(exc=exc, countdown=120)


@celery_app.task(bind=True, max_retries=2)
def batch_process_documents(self, document_ids: list):
    """Procesa múltiples documentos en batch.
    
    Args:
        document_ids: Lista de IDs de documentos
    """
    import asyncio
    
    async def _batch_process():
        results = []
        
        for doc_id in document_ids:
            try:
                # Encolar cada documento individualmente
                result = process_document_async.delay(doc_id)
                results.append({
                    "document_id": doc_id,
                    "task_id": result.id,
                    "status": "queued"
                })
            except Exception as e:
                results.append({
                    "document_id": doc_id,
                    "error": str(e),
                    "status": "failed"
                })
        
        return {
            "status": "batch_queued",
            "total": len(document_ids),
            "results": results
        }
    
    return asyncio.run(_batch_process())


@celery_app.task(bind=True, max_retries=5)
def retry_failed_documents(self):
    """Reintenta documentos que fallaron anteriormente."""
    import asyncio
    
    async def _retry():
        from sqlalchemy import select
        
        async with async_session_maker() as db:
            # Buscar documentos fallidos
            result = await db.execute(
                select(Document).where(
                    Document.status.in_([DocumentStatus.FAILED.value, DocumentStatus.RETRYING.value])
                ).limit(10)
            )
            failed_docs = result.scalars().all()
            
            if not failed_docs:
                logger.info("No failed documents to retry")
                return {"status": "no_failed_documents"}
            
            # Actualizar estado a retrying
            for doc in failed_docs:
                doc.status = DocumentStatus.RETRYING.value
            
            await db.commit()
            
            # Re-encolar para procesamiento
            queued = []
            for doc in failed_docs:
                task = process_document_async.delay(str(doc.id))
                queued.append({
                    "document_id": str(doc.id),
                    "task_id": task.id
                })
            
            logger.info(f"Queued {len(queued)} failed documents for retry")
            
            return {
                "status": "retry_queued",
                "count": len(queued),
                "documents": queued
            }
    
    try:
        return asyncio.run(_retry())
    except Exception as exc:
        logger.error(f"Retry task failed: {exc}")
        self.retry(exc=exc, countdown=300)


@celery_app.task
def cleanup_old_extractions(days: int = 30):
    """Limpia extracciones antiguas para ahorrar espacio.
    
    Args:
        days: Eliminar extracciones más antiguas que N días
    """
    import asyncio
    from datetime import datetime, timedelta
    from sqlalchemy import delete
    
    async def _cleanup():
        from app.models.rhtools import DocumentTextExtraction
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with async_session_maker() as db:
            result = await db.execute(
                delete(DocumentTextExtraction).where(
                    DocumentTextExtraction.created_at < cutoff_date
                )
            )
            await db.commit()
            
            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} old text extractions")
            
            return {
                "status": "completed",
                "deleted_count": deleted_count
            }
    
    return asyncio.run(_cleanup())


# Crear cadena de tareas para procesamiento completo
def create_document_processing_chain(document_id: str):
    """Crea una cadena de tareas para procesar un documento completo.
    
    Args:
        document_id: ID del documento
        
    Returns:
        Cadena de Celery
    """
    return chain(
        process_document_async.s(document_id),
        # Se puede agregar más tareas aquí
        # por ejemplo: evaluate_candidate_async.s()
    )
