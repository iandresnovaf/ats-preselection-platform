"""Pipeline de procesamiento de documentos con estados."""
import logging
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.services.extraction.models import (
    ProcessingStatus, ParseResult, ExtractionResult,
    PipelineJob, DocumentType
)
from app.services.extraction.document_parser import DocumentParser
from app.services.extraction.assessment_extractor import AssessmentExtractor
from app.services.extraction.cv_extractor import CVExtractor
from app.services.extraction.interview_extractor import InterviewExtractor
from app.validators.data_validator import DataValidator
from app.validators.data_cleaner import DataCleaner
from app.models.rhtools import Document, DocumentTextExtraction

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Error en el pipeline."""
    pass


class DocumentPipeline:
    """Pipeline de procesamiento de documentos con gestión de estados."""
    
    def __init__(self, db_session: AsyncSession):
        """Inicializa el pipeline.
        
        Args:
            db_session: Sesión de base de datos
        """
        self.db = db_session
        self.parser = DocumentParser()
        self.assessment_extractor = AssessmentExtractor()
        self.cv_extractor = CVExtractor()
        self.interview_extractor = InterviewExtractor()
        self.validator = DataValidator()
        self.cleaner = DataCleaner()
    
    async def process(self, document_id: str) -> PipelineJob:
        """Procesa un documento a través del pipeline completo.
        
        Estados: uploaded → parsing → extracting → validating → completed/error
        
        Args:
            document_id: ID del documento
            
        Returns:
            PipelineJob con el resultado
        """
        job_id = str(uuid.uuid4())
        start_time = time.time()
        
        job = PipelineJob(
            job_id=job_id,
            document_id=document_id,
            status=ProcessingStatus.UPLOADED,
            current_step="starting",
            started_at=datetime.utcnow()
        )
        
        logger.info(f"Iniciando pipeline para documento {document_id}, job {job_id}")
        
        try:
            # 1. Obtener documento
            document = await self._get_document(document_id)
            if not document:
                raise PipelineError(f"Documento no encontrado: {document_id}")
            
            # 2. Verificar hash para deduplicación
            existing_id = await self.parser.dedupe_by_hash(document.checksum, self.db)
            if existing_id and existing_id != document_id:
                logger.info(f"Documento duplicado detectado: {document_id} es igual a {existing_id}")
                # Podríamos copiar los datos del documento existente
            
            # 3. Update status: parsing
            await self._update_document_status(document_id, ProcessingStatus.PARSING)
            job.status = ProcessingStatus.PARSING
            job.current_step = "parsing"
            
            # Parsear documento
            parse_result = await self.parser.parse_document(
                document_id=document_id,
                file_path=document.file_path,
                mime_type=document.mime_type
            )
            
            if parse_result.status == ProcessingStatus.ERROR:
                raise PipelineError(f"Error en parsing: {parse_result.error_message}")
            
            # Guardar texto extraído
            await self._save_text_extraction(document_id, parse_result)
            
            # 4. Update status: extracting
            await self._update_document_status(document_id, ProcessingStatus.EXTRACTING)
            job.status = ProcessingStatus.EXTRACTING
            job.current_step = "extracting"
            
            # Extraer datos según el tipo
            extraction_result = await self._extract_data(
                parse_result.document_type,
                parse_result.text,
                document_id
            )
            
            # 5. Update status: validating
            await self._update_document_status(document_id, ProcessingStatus.VALIDATING)
            job.status = ProcessingStatus.VALIDATING
            job.current_step = "validating"
            
            # Validar datos
            validation_result = await self._validate_data(
                parse_result.document_type,
                extraction_result.data
            )
            
            if not validation_result.is_valid:
                logger.warning(f"Validación fallida para {document_id}: {validation_result.errors}")
            
            # 6. Guardar datos extraídos
            await self._save_extracted_data(
                document_id,
                parse_result.document_type,
                extraction_result,
                validation_result
            )
            
            # 7. Update status: completed
            await self._update_document_status(document_id, ProcessingStatus.COMPLETED)
            job.status = ProcessingStatus.COMPLETED
            job.current_step = "completed"
            job.completed_at = datetime.utcnow()
            
            job.result = {
                "document_type": parse_result.document_type.value,
                "confidence": extraction_result.confidence,
                "validation_valid": validation_result.is_valid,
                "warnings": [w.message for w in validation_result.warnings],
            }
            
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(
                f"Pipeline completado para {document_id} en {processing_time}ms: "
                f"tipo={parse_result.document_type.value}, "
                f"confianza={extraction_result.confidence:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error en pipeline para {document_id}: {e}")
            
            # Update status: error
            await self._update_document_status(document_id, ProcessingStatus.ERROR)
            job.status = ProcessingStatus.ERROR
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            
            # Guardar error en extraction
            await self._save_extraction_error(document_id, str(e))
        
        return job
    
    async def process_manual_review(self, document_id: str, 
                                   confirmed_data: Dict[str, Any]) -> PipelineJob:
        """Procesa confirmación manual de datos extraídos.
        
        Args:
            document_id: ID del documento
            confirmed_data: Datos confirmados/editados por el usuario
            
        Returns:
            PipelineJob con el resultado
        """
        job_id = str(uuid.uuid4())
        
        job = PipelineJob(
            job_id=job_id,
            document_id=document_id,
            status=ProcessingStatus.MANUAL_REVIEW,
            current_step="manual_confirmation",
            started_at=datetime.utcnow()
        )
        
        try:
            # Validar datos confirmados
            validation_result = await self._validate_data(
                DocumentType(confirmed_data.get('document_type', 'other')),
                confirmed_data
            )
            
            if not validation_result.is_valid:
                job.status = ProcessingStatus.ERROR
                job.error_message = "Datos confirmados no pasaron validación"
                job.completed_at = datetime.utcnow()
                return job
            
            # Guardar datos confirmados
            await self._save_confirmed_data(document_id, confirmed_data, validation_result)
            
            # Update status: confirmed
            job.status = ProcessingStatus.CONFIRMED
            job.current_step = "confirmed"
            job.completed_at = datetime.utcnow()
            
            logger.info(f"Datos confirmados manualmente para documento {document_id}")
            
        except Exception as e:
            logger.error(f"Error en confirmación manual para {document_id}: {e}")
            job.status = ProcessingStatus.ERROR
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
        
        return job
    
    async def get_status(self, document_id: str) -> Optional[ProcessingStatus]:
        """Obtiene el estado actual de un documento.
        
        Args:
            document_id: ID del documento
            
        Returns:
            Estado del documento
        """
        document = await self._get_document(document_id)
        if document:
            # Intentar mapear el estado del documento a ProcessingStatus
            status_map = {
                'pending': ProcessingStatus.UPLOADED,
                'processing': ProcessingStatus.PARSING,
                'processed': ProcessingStatus.COMPLETED,
                'error': ProcessingStatus.ERROR,
            }
            return status_map.get(document.status, ProcessingStatus.UPLOADED)
        return None
    
    async def _get_document(self, document_id: str) -> Optional[Document]:
        """Obtiene un documento por ID.
        
        Args:
            document_id: ID del documento
            
        Returns:
            Documento o None
        """
        from uuid import UUID
        result = await self.db.execute(
            select(Document).where(Document.id == UUID(document_id))
        )
        return result.scalar_one_or_none()
    
    async def _update_document_status(self, document_id: str, 
                                      status: ProcessingStatus):
        """Actualiza el estado de un documento.
        
        Args:
            document_id: ID del documento
            status: Nuevo estado
        """
        from uuid import UUID
        
        # Mapear ProcessingStatus a DocumentStatus
        status_map = {
            ProcessingStatus.UPLOADED: 'pending',
            ProcessingStatus.PARSING: 'processing',
            ProcessingStatus.EXTRACTING: 'processing',
            ProcessingStatus.VALIDATING: 'processing',
            ProcessingStatus.COMPLETED: 'processed',
            ProcessingStatus.ERROR: 'error',
            ProcessingStatus.MANUAL_REVIEW: 'processing',
            ProcessingStatus.CONFIRMED: 'processed',
        }
        
        mapped_status = status_map.get(status, 'pending')
        
        await self.db.execute(
            update(Document)
            .where(Document.id == UUID(document_id))
            .values(status=mapped_status, updated_at=datetime.utcnow())
        )
        await self.db.commit()
    
    async def _save_text_extraction(self, document_id: str, parse_result: ParseResult):
        """Guarda la extracción de texto.
        
        Args:
            document_id: ID del documento
            parse_result: Resultado del parsing
        """
        from uuid import UUID
        
        extraction = DocumentTextExtraction(
            document_id=UUID(document_id),
            status='completed',
            extracted_text=parse_result.text,
            extracted_text_clean=self.cleaner.clean_text(parse_result.text),
            extracted_metadata=parse_result.metadata,
            extraction_engine='document_parser',
            processed_at=datetime.utcnow()
        )
        
        self.db.add(extraction)
        await self.db.commit()
    
    async def _extract_data(self, document_type: DocumentType, text: str, 
                           document_id: str) -> ExtractionResult:
        """Extrae datos según el tipo de documento.
        
        Args:
            document_type: Tipo de documento
            text: Texto extraído
            document_id: ID del documento
            
        Returns:
            Resultado de extracción
        """
        if document_type == DocumentType.ASSESSMENT:
            data = await self.assessment_extractor.extract_from_text(text)
            return ExtractionResult(
                document_type=document_type,
                confidence=0.85 if data.scores else 0.5,
                data=data.dict()
            )
        
        elif document_type == DocumentType.CV:
            data = await self.cv_extractor.extract_from_text(text)
            return ExtractionResult(
                document_type=document_type,
                confidence=0.80 if data.full_name else 0.5,
                data=data.dict()
            )
        
        elif document_type == DocumentType.INTERVIEW:
            data = await self.interview_extractor.extract_from_text(text)
            return ExtractionResult(
                document_type=document_type,
                confidence=0.75 if data.summary else 0.5,
                data=data.dict()
            )
        
        else:
            return ExtractionResult(
                document_type=DocumentType.OTHER,
                confidence=0.3,
                data={"raw_text": text[:1000]}
            )
    
    async def _validate_data(self, document_type: DocumentType, 
                            data: Dict[str, Any]):
        """Valida datos extraídos.
        
        Args:
            document_type: Tipo de documento
            data: Datos a validar
            
        Returns:
            Resultado de validación
        """
        if document_type == DocumentType.ASSESSMENT:
            return self.validator.validate_assessment_data(data)
        elif document_type == DocumentType.CV:
            return self.validator.validate_cv_data(data)
        elif document_type == DocumentType.INTERVIEW:
            return self.validator.validate_interview_data(data)
        else:
            # Para otros tipos, validación mínima
            return self.validator.validate_cv_data(data)
    
    async def _save_extracted_data(self, document_id: str, 
                                   document_type: DocumentType,
                                   extraction: ExtractionResult,
                                   validation: Any):
        """Guarda los datos extraídos en la base de datos.
        
        Args:
            document_id: ID del documento
            document_type: Tipo de documento
            extraction: Resultado de extracción
            validation: Resultado de validación
        """
        from uuid import UUID
        
        # Actualizar extracción con datos parseados
        result = await self.db.execute(
            select(DocumentTextExtraction).where(
                DocumentTextExtraction.document_id == UUID(document_id)
            )
        )
        extraction_record = result.scalar_one_or_none()
        
        if extraction_record:
            extraction_record.parsed_data = {
                "document_type": extraction.document_type.value,
                "confidence": extraction.confidence,
                "data": extraction.data,
                "validation": {
                    "is_valid": validation.is_valid,
                    "errors": [e.dict() for e in validation.errors],
                    "warnings": [w.dict() for w in validation.warnings],
                },
                "normalized_data": validation.normalized_data,
            }
            await self.db.commit()
        
        # Guardar en tablas específicas según el tipo
        if document_type == DocumentType.ASSESSMENT:
            await self._save_assessment_scores(document_id, extraction.data)
    
    async def _save_assessment_scores(self, document_id: str, data: Dict[str, Any]):
        """Guarda scores de assessment en filas (no columnas).
        
        Nota: Este método guarda en parsed_data del documento.
        Para guardar en assessment_scores de core_ats, se requiere
        una aplicación vinculada.
        
        Args:
            document_id: ID del documento
            data: Datos del assessment
        """
        # Los scores se guardan en el parsed_data del DocumentTextExtraction
        # Para integrar con core_ats, el usuario debe confirmar la extracción
        # y luego el sistema puede crear un Assessment y AssessmentScore
        scores = data.get('scores', [])
        logger.info(f"Assessment extraído con {len(scores)} scores para documento {document_id}")
    
    async def _save_confirmed_data(self, document_id: str, 
                                   data: Dict[str, Any],
                                   validation: Any):
        """Guarda datos confirmados manualmente.
        
        Args:
            document_id: ID del documento
            data: Datos confirmados
            validation: Resultado de validación
        """
        from uuid import UUID
        
        result = await self.db.execute(
            select(DocumentTextExtraction).where(
                DocumentTextExtraction.document_id == UUID(document_id)
            )
        )
        extraction_record = result.scalar_one_or_none()
        
        if extraction_record:
            extraction_record.parsed_data = {
                "document_type": data.get('document_type', 'other'),
                "confidence": 1.0,  # Datos confirmados manualmente tienen confianza 100%
                "data": data,
                "validation": {
                    "is_valid": validation.is_valid,
                    "errors": [e.dict() for e in validation.errors],
                    "warnings": [w.dict() for w in validation.warnings],
                },
                "normalized_data": validation.normalized_data,
                "manual_confirmation": True,
                "confirmed_at": datetime.utcnow().isoformat(),
            }
            await self.db.commit()
    
    async def _save_extraction_error(self, document_id: str, error_message: str):
        """Guarda error de extracción.
        
        Args:
            document_id: ID del documento
            error_message: Mensaje de error
        """
        from uuid import UUID
        
        # Crear registro de extracción con error
        extraction = DocumentTextExtraction(
            document_id=UUID(document_id),
            status='failed',
            error_message=error_message,
            retry_count=0
        )
        
        self.db.add(extraction)
        await self.db.commit()
