"""Servicio para gestión de pipelines en RHTools."""
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from app.models.rhtools import PipelineTemplate, PipelineStage, StageRequiredField
from app.schemas import (
    PipelineTemplateCreate,
    PipelineTemplateUpdate,
    PipelineStageCreate,
    PipelineStageUpdate,
    ReorderStagesRequest,
)


class PipelineService:
    """Servicio para gestionar pipelines en RHTools."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_template_by_id(self, template_id: str) -> Optional[PipelineTemplate]:
        """Obtener template de pipeline por ID con sus stages."""
        result = await self.db.execute(
            select(PipelineTemplate)
            .options(selectinload(PipelineTemplate.stages).selectinload(PipelineStage.required_fields))
            .where(PipelineTemplate.id == template_id)
        )
        return result.scalar_one_or_none()
    
    async def get_stage_by_id(self, stage_id: str) -> Optional[PipelineStage]:
        """Obtener stage por ID."""
        result = await self.db.execute(
            select(PipelineStage)
            .options(selectinload(PipelineStage.required_fields))
            .where(PipelineStage.id == stage_id)
        )
        return result.scalar_one_or_none()
    
    async def list_templates(
        self,
        client_id: Optional[str] = None,
        pipeline_type: Optional[str] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[PipelineTemplate], int]:
        """Listar templates de pipeline con filtros."""
        query = select(PipelineTemplate)
        
        # Aplicar filtros
        filters = []
        if client_id:
            filters.append(PipelineTemplate.client_id == client_id)
        if pipeline_type:
            filters.append(PipelineTemplate.pipeline_type == pipeline_type)
        if is_active is not None:
            filters.append(PipelineTemplate.is_active == is_active)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Ordenar y paginar
        query = query.order_by(desc(PipelineTemplate.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        templates = result.scalars().all()
        
        return templates, total
    
    async def create_pipeline_template(
        self,
        data: PipelineTemplateCreate,
        created_by: Optional[str] = None
    ) -> PipelineTemplate:
        """Crear nuevo template de pipeline."""
        template = PipelineTemplate(
            client_id=data.client_id,
            name=data.name,
            description=data.description,
            pipeline_type=data.pipeline_type,
            is_default=data.is_default,
            is_active=True,
        )
        
        self.db.add(template)
        await self.db.flush()
        
        # Crear stages si se proporcionan
        if data.stages:
            for idx, stage_data in enumerate(data.stages):
                stage = PipelineStage(
                    pipeline_id=template.id,
                    name=stage_data.name,
                    description=stage_data.description,
                    color=stage_data.color,
                    is_required=stage_data.is_required,
                    is_final=stage_data.is_final,
                    sla_hours=stage_data.sla_hours,
                    auto_advance=stage_data.auto_advance,
                    order_index=stage_data.order_index or idx,
                    is_active=True,
                )
                self.db.add(stage)
                await self.db.flush()
                
                # Crear campos requeridos
                if stage_data.required_fields:
                    for field_idx, field_data in enumerate(stage_data.required_fields):
                        field = StageRequiredField(
                            stage_id=stage.id,
                            field_name=field_data.field_name,
                            field_type=field_data.field_type,
                            field_label=field_data.field_label,
                            is_required=field_data.is_required,
                            validation_rules=field_data.validation_rules,
                            help_text=field_data.help_text,
                            default_value=field_data.default_value,
                            order_index=field_data.order_index or field_idx,
                        )
                        self.db.add(field)
        
        await self.db.flush()
        await self.db.refresh(template)
        
        return template
    
    async def update_pipeline_template(
        self,
        template_id: str,
        data: PipelineTemplateUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[PipelineTemplate]:
        """Actualizar template de pipeline."""
        template = await self.get_template_by_id(template_id)
        if not template:
            return None
        
        if data.name is not None:
            template.name = data.name
        if data.description is not None:
            template.description = data.description
        if data.is_default is not None:
            template.is_default = data.is_default
        if data.is_active is not None:
            template.is_active = data.is_active
        
        template.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(template)
        
        return template
    
    async def delete_pipeline_template(self, template_id: str) -> bool:
        """Eliminar template de pipeline."""
        template = await self.get_template_by_id(template_id)
        if not template:
            return False
        
        await self.db.delete(template)
        await self.db.flush()
        
        return True
    
    async def create_stage(
        self,
        template_id: str,
        data: PipelineStageCreate,
        created_by: Optional[str] = None
    ) -> Optional[PipelineStage]:
        """Crear nuevo stage en un pipeline."""
        # Verificar que el template existe
        template = await self.get_template_by_id(template_id)
        if not template:
            return None
        
        # Obtener el máximo order_index actual
        result = await self.db.execute(
            select(func.max(PipelineStage.order_index))
            .where(PipelineStage.pipeline_id == template_id)
        )
        max_order = result.scalar() or 0
        
        stage = PipelineStage(
            pipeline_id=template_id,
            name=data.name,
            description=data.description,
            color=data.color,
            is_required=data.is_required,
            is_final=data.is_final,
            sla_hours=data.sla_hours,
            auto_advance=data.auto_advance,
            order_index=data.order_index or (max_order + 1),
            is_active=True,
        )
        
        self.db.add(stage)
        await self.db.flush()
        await self.db.refresh(stage)
        
        return stage
    
    async def update_stage(
        self,
        stage_id: str,
        data: PipelineStageUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[PipelineStage]:
        """Actualizar stage."""
        stage = await self.get_stage_by_id(stage_id)
        if not stage:
            return None
        
        if data.name is not None:
            stage.name = data.name
        if data.description is not None:
            stage.description = data.description
        if data.color is not None:
            stage.color = data.color
        if data.is_required is not None:
            stage.is_required = data.is_required
        if data.is_final is not None:
            stage.is_final = data.is_final
        if data.sla_hours is not None:
            stage.sla_hours = data.sla_hours
        if data.auto_advance is not None:
            stage.auto_advance = data.auto_advance
        if data.order_index is not None:
            stage.order_index = data.order_index
        if data.is_active is not None:
            stage.is_active = data.is_active
        
        stage.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(stage)
        
        return stage
    
    async def delete_stage(self, stage_id: str) -> bool:
        """Eliminar stage."""
        stage = await self.get_stage_by_id(stage_id)
        if not stage:
            return False
        
        await self.db.delete(stage)
        await self.db.flush()
        
        return True
    
    async def reorder_stages(
        self,
        template_id: str,
        data: ReorderStagesRequest,
        updated_by: Optional[str] = None
    ) -> bool:
        """Reordenar stages de un pipeline."""
        # Verificar que el template existe
        template = await self.get_template_by_id(template_id)
        if not template:
            return False
        
        # Actualizar el order_index de cada stage
        for idx, stage_id in enumerate(data.stage_ids):
            result = await self.db.execute(
                select(PipelineStage).where(
                    and_(
                        PipelineStage.id == stage_id,
                        PipelineStage.pipeline_id == template_id
                    )
                )
            )
            stage = result.scalar_one_or_none()
            if stage:
                stage.order_index = idx
        
        await self.db.flush()
        return True
    
    async def validate_stage_transition(
        self,
        submission_id: str,
        from_stage_id: Optional[str],
        to_stage_id: str,
        user_id: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validar si una transición de etapa es válida.
        
        Returns:
            (is_valid, error_message)
        """
        # Obtener el stage destino
        to_stage = await self.get_stage_by_id(to_stage_id)
        if not to_stage:
            return False, "Stage destino no encontrado"
        
        # Si no hay stage origen, es válido (nueva submission)
        if not from_stage_id:
            return True, None
        
        # Obtener stage origen
        from_stage = await self.get_stage_by_id(from_stage_id)
        if not from_stage:
            return False, "Stage origen no encontrado"
        
        # Verificar que ambos stages pertenecen al mismo pipeline
        if from_stage.pipeline_id != to_stage.pipeline_id:
            return False, "Los stages no pertenecen al mismo pipeline"
        
        # Aquí se pueden agregar más reglas de validación
        # Por ejemplo, no permitir saltar etapas requeridas
        
        return True, None
    
    async def get_pipeline_for_search(self, client_id: str, job_opening_id: str) -> Optional[PipelineTemplate]:
        """
        Obtener el pipeline apropiado para una búsqueda.
        Por defecto retorna el pipeline default del cliente.
        """
        # Buscar pipeline default del cliente
        result = await self.db.execute(
            select(PipelineTemplate)
            .options(selectinload(PipelineTemplate.stages))
            .where(
                and_(
                    PipelineTemplate.client_id == client_id,
                    PipelineTemplate.is_default == True,
                    PipelineTemplate.is_active == True
                )
            )
        )
        template = result.scalar_one_or_none()
        
        if not template:
            # Si no hay default, retornar el primero activo
            result = await self.db.execute(
                select(PipelineTemplate)
                .options(selectinload(PipelineTemplate.stages))
                .where(
                    and_(
                        PipelineTemplate.client_id == client_id,
                        PipelineTemplate.is_active == True
                    )
                )
                .order_by(PipelineTemplate.created_at)
                .limit(1)
            )
            template = result.scalar_one_or_none()
        
        return template
    
    async def get_required_fields_for_stage(self, stage_id: str) -> List[StageRequiredField]:
        """Obtener campos requeridos para un stage."""
        result = await self.db.execute(
            select(StageRequiredField)
            .where(
                and_(
                    StageRequiredField.stage_id == stage_id,
                    StageRequiredField.is_required == True
                )
            )
            .order_by(StageRequiredField.order_index)
        )
        return result.scalars().all()
