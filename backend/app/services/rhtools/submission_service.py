"""Servicio para gestión de submissions en RHTools."""
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from app.models.rhtools import Submission, SubmissionStageHistory, PipelineStage
from app.schemas import SubmissionCreate, SubmissionUpdate, ChangeStageRequest
from app.services.rhtools.pipeline_service import PipelineService


class SubmissionService:
    """Servicio para gestionar submissions en RHTools."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pipeline_service = PipelineService(db)
    
    async def get_by_id(self, submission_id: str) -> Optional[Submission]:
        """Obtener submission por ID."""
        result = await self.db.execute(
            select(Submission)
            .options(
                selectinload(Submission.stage_history),
                selectinload(Submission.candidate),
                selectinload(Submission.client),
                selectinload(Submission.job_opening),
            )
            .where(Submission.id == submission_id)
        )
        return result.scalar_one_or_none()
    
    async def list_submissions(
        self,
        client_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        job_opening_id: Optional[str] = None,
        status: Optional[str] = None,
        current_stage_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Submission], int]:
        """Listar submissions con filtros y paginación."""
        query = select(Submission)
        
        # Aplicar filtros
        filters = []
        if client_id:
            filters.append(Submission.client_id == client_id)
        if candidate_id:
            filters.append(Submission.candidate_id == candidate_id)
        if job_opening_id:
            filters.append(Submission.job_opening_id == job_opening_id)
        if status:
            filters.append(Submission.status == status)
        if current_stage_id:
            filters.append(Submission.current_stage_id == current_stage_id)
        if owner_id:
            filters.append(Submission.owner_user_id == owner_id)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Ordenar y paginar
        query = query.order_by(desc(Submission.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        submissions = result.scalars().all()
        
        return submissions, total
    
    async def create_submission(
        self,
        data: SubmissionCreate,
        created_by: Optional[str] = None
    ) -> Submission:
        """Crear nueva submission."""
        # Si no se especifica pipeline, obtener el default del cliente
        pipeline_id = data.pipeline_id
        current_stage_id = None
        
        if not pipeline_id:
            pipeline = await self.pipeline_service.get_pipeline_for_search(
                client_id=data.client_id,
                job_opening_id=data.job_opening_id
            )
            if pipeline:
                pipeline_id = pipeline.id
                # Obtener el primer stage
                if pipeline.stages:
                    first_stage = min(pipeline.stages, key=lambda s: s.order_index)
                    current_stage_id = first_stage.id
        
        submission = Submission(
            candidate_id=data.candidate_id,
            client_id=data.client_id,
            job_opening_id=data.job_opening_id,
            pipeline_id=pipeline_id,
            current_stage_id=current_stage_id,
            status="active",
            priority=data.priority,
            salary_expectation=data.salary_expectation,
            currency=data.currency,
            source=data.source,
            source_detail=data.source_detail,
            notes=data.notes,
            custom_fields=data.custom_fields,
            applied_at=datetime.utcnow(),
        )
        
        self.db.add(submission)
        await self.db.flush()
        
        # Crear entrada en historial si hay stage inicial
        if current_stage_id:
            history_entry = SubmissionStageHistory(
                submission_id=submission.id,
                from_stage_id=None,
                to_stage_id=current_stage_id,
                changed_by=created_by,
                changed_at=datetime.utcnow(),
                notes="Submission creada",
            )
            self.db.add(history_entry)
        
        await self.db.flush()
        await self.db.refresh(submission)
        
        return submission
    
    async def update_submission(
        self,
        submission_id: str,
        data: SubmissionUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[Submission]:
        """Actualizar submission."""
        submission = await self.get_by_id(submission_id)
        if not submission:
            return None
        
        # Actualizar campos
        if data.priority is not None:
            submission.priority = data.priority
        if data.salary_expectation is not None:
            submission.salary_expectation = data.salary_expectation
        if data.salary_offered is not None:
            submission.salary_offered = data.salary_offered
        if data.currency is not None:
            submission.currency = data.currency
        if data.status is not None:
            submission.status = data.status
            # Actualizar fechas según estado
            if data.status == "hired":
                submission.hired_at = datetime.utcnow()
            elif data.status == "rejected":
                submission.rejected_at = datetime.utcnow()
        if data.notes is not None:
            submission.notes = data.notes
        if data.custom_fields is not None:
            submission.custom_fields = data.custom_fields
        if data.owner_user_id is not None:
            submission.owner_user_id = data.owner_user_id
        
        submission.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(submission)
        
        return submission
    
    async def change_stage(
        self,
        submission_id: str,
        data: ChangeStageRequest,
        changed_by: Optional[str] = None
    ) -> Optional[Submission]:
        """Cambiar el stage de una submission."""
        submission = await self.get_by_id(submission_id)
        if not submission:
            return None
        
        # Validar transición
        is_valid, error = await self.pipeline_service.validate_stage_transition(
            submission_id=submission_id,
            from_stage_id=submission.current_stage_id,
            to_stage_id=data.stage_id,
            user_id=changed_by
        )
        
        if not is_valid:
            raise ValueError(f"Transición inválida: {error}")
        
        # Calcular duración en stage anterior
        duration_seconds = None
        if submission.current_stage_id:
            # Buscar la última entrada de historial para este stage
            result = await self.db.execute(
                select(SubmissionStageHistory)
                .where(
                    and_(
                        SubmissionStageHistory.submission_id == submission_id,
                        SubmissionStageHistory.to_stage_id == submission.current_stage_id
                    )
                )
                .order_by(desc(SubmissionStageHistory.changed_at))
                .limit(1)
            )
            last_entry = result.scalar_one_or_none()
            if last_entry:
                duration = datetime.utcnow() - last_entry.changed_at
                duration_seconds = int(duration.total_seconds())
        
        # Crear entrada en historial
        history_entry = SubmissionStageHistory(
            submission_id=submission_id,
            from_stage_id=submission.current_stage_id,
            to_stage_id=data.stage_id,
            changed_by=changed_by,
            changed_at=datetime.utcnow(),
            notes=data.notes,
            reason=data.reason,
            captured_data=data.captured_data,
            duration_seconds=duration_seconds,
        )
        self.db.add(history_entry)
        
        # Actualizar submission
        old_stage_id = submission.current_stage_id
        submission.current_stage_id = data.stage_id
        submission.updated_at = datetime.utcnow()
        
        # Actualizar timestamps según el stage
        stage = await self.pipeline_service.get_stage_by_id(data.stage_id)
        if stage:
            if "interview" in stage.name.lower() and not submission.first_contact_at:
                submission.first_contact_at = datetime.utcnow()
            if stage.is_final:
                # Si es etapa final, actualizar estado
                if "hired" in stage.name.lower() or "offer" in stage.name.lower():
                    submission.status = "hired"
                    submission.hired_at = datetime.utcnow()
                elif "reject" in stage.name.lower():
                    submission.status = "rejected"
                    submission.rejected_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(submission)
        
        return submission
    
    async def get_stage_history(self, submission_id: str) -> List[SubmissionStageHistory]:
        """Obtener historial de cambios de stage."""
        result = await self.db.execute(
            select(SubmissionStageHistory)
            .options(
                selectinload(SubmissionStageHistory.from_stage),
                selectinload(SubmissionStageHistory.to_stage),
            )
            .where(SubmissionStageHistory.submission_id == submission_id)
            .order_by(desc(SubmissionStageHistory.changed_at))
        )
        return result.scalars().all()
    
    async def enforce_stage_rules(
        self,
        submission_id: str,
        stage_id: str,
        data: Dict[str, Any]
    ) -> tuple[bool, Optional[List[str]]]:
        """
        Verificar que se cumplan las reglas del stage.
        
        Returns:
            (is_valid, list of missing_fields)
        """
        # Obtener campos requeridos
        required_fields = await self.pipeline_service.get_required_fields_for_stage(stage_id)
        
        missing_fields = []
        for field in required_fields:
            if field.is_required:
                field_value = data.get(field.field_name)
                if field_value is None or field_value == "":
                    missing_fields.append(field.field_label or field.field_name)
        
        if missing_fields:
            return False, missing_fields
        
        return True, None
    
    async def get_submission_stats(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtener estadísticas de submissions."""
        query = select(Submission)
        if client_id:
            query = query.where(Submission.client_id == client_id)
        
        # Total
        total_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar()
        
        # Por estado
        status_counts = {}
        for status in ["active", "on_hold", "withdrawn", "hired", "rejected"]:
            count_result = await self.db.execute(
                select(func.count())
                .select_from(Submission)
                .where(
                    and_(
                        Submission.status == status,
                        Submission.client_id == client_id if client_id else True
                    )
                )
            )
            status_counts[status] = count_result.scalar()
        
        return {
            "total": total,
            "by_status": status_counts,
        }
