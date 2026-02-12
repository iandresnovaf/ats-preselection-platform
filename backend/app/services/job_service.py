"""Servicio para gestión de ofertas de trabajo."""
from typing import List, Optional, Tuple
from datetime import datetime
import base64
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models import JobOpening, JobStatus, Candidate
from app.schemas import JobOpeningCreate, JobOpeningUpdate, JobRequirements


def encode_cursor(created_at: datetime) -> str:
    """Codificar fecha de creación como cursor base64."""
    data = {"created_at": created_at.isoformat()}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> datetime:
    """Decodificar cursor a fecha de creación."""
    # Agregar padding si es necesario
    padding = 4 - len(cursor) % 4
    if padding != 4:
        cursor += "=" * padding
    
    data = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    return datetime.fromisoformat(data["created_at"])


class JobService:
    """Servicio para gestionar ofertas de trabajo."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, job_id: str) -> Optional[JobOpening]:
        """Obtener oferta por ID."""
        result = await self.db.execute(
            select(JobOpening).where(JobOpening.id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id_with_candidates(self, job_id: str) -> Optional[JobOpening]:
        """Obtener oferta con sus candidatos."""
        result = await self.db.execute(
            select(JobOpening)
            .where(JobOpening.id == job_id)
            .options(selectinload(JobOpening.candidates))
        )
        return result.scalar_one_or_none()
    
    async def list_jobs(
        self,
        status: Optional[str] = None,
        assigned_consultant_id: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[JobOpening], int]:
        """Listar ofertas con filtros y paginación."""
        # Query base
        query = select(JobOpening)
        
        # Aplicar filtros
        filters = []
        if status:
            filters.append(JobOpening.status == status)
        if assigned_consultant_id:
            filters.append(JobOpening.assigned_consultant_id == assigned_consultant_id)
        if search:
            search_filter = or_(
                JobOpening.title.ilike(f"%{search}%"),
                JobOpening.department.ilike(f"%{search}%"),
                JobOpening.location.ilike(f"%{search}%"),
            )
            filters.append(search_filter)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Ordenar y paginar
        query = query.order_by(desc(JobOpening.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        jobs = result.scalars().all()
        
        return jobs, total
    
    async def list_jobs_cursor(
        self,
        cursor: Optional[str] = None,
        limit: int = 20,
        status: Optional[str] = None,
        assigned_consultant_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[JobOpening], Optional[str]]:
        """
        Listar ofertas con paginación basada en cursor (más eficiente que OFFSET).
        
        Args:
            cursor: Cursor de paginación (opcional)
            limit: Cantidad de items por página
            status: Filtro por estado
            assigned_consultant_id: Filtro por consultor asignado
            search: Búsqueda por título, departamento o ubicación
            
        Returns:
            Tupla de (lista de jobs, siguiente cursor o None)
        """
        # Query base ordenada por created_at descendente
        query = select(JobOpening).order_by(JobOpening.created_at.desc())
        
        # Aplicar filtros
        if status:
            query = query.where(JobOpening.status == status)
        if assigned_consultant_id:
            query = query.where(JobOpening.assigned_consultant_id == assigned_consultant_id)
        if search:
            search_filter = or_(
                JobOpening.title.ilike(f"%{search}%"),
                JobOpening.department.ilike(f"%{search}%"),
                JobOpening.location.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
        
        # Aplicar cursor (paginación)
        if cursor:
            try:
                cursor_date = decode_cursor(cursor)
                query = query.where(JobOpening.created_at < cursor_date)
            except Exception:
                # Cursor inválido, ignorar y retornar primera página
                pass
        
        # Pedir limit + 1 para saber si hay más páginas
        query = query.limit(limit + 1)
        
        result = await self.db.execute(query)
        jobs = list(result.scalars().all())
        
        # Determinar si hay siguiente página
        next_cursor = None
        if len(jobs) > limit:
            next_cursor = encode_cursor(jobs[-1].created_at)
            jobs = jobs[:limit]
        
        return jobs, next_cursor
    
    async def create_job(self, data: JobOpeningCreate) -> JobOpening:
        """Crear nueva oferta de trabajo."""
        # Convertir requirements a dict si existe
        requirements = None
        if data.requirements:
            requirements = data.requirements.model_dump()
        
        job = JobOpening(
            title=data.title,
            description=data.description,
            department=data.department,
            location=data.location,
            seniority=data.seniority,
            sector=data.sector,
            requirements=requirements,
            salary_range_min=data.salary_range_min,
            salary_range_max=data.salary_range_max,
            employment_type=data.employment_type or "full-time",
            assigned_consultant_id=data.assigned_consultant_id,
            status=JobStatus.DRAFT.value,
            is_active=True,
        )
        
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        
        return job
    
    async def update_job(
        self, 
        job_id: str, 
        data: JobOpeningUpdate
    ) -> Optional[JobOpening]:
        """Actualizar oferta de trabajo."""
        job = await self.get_by_id(job_id)
        if not job:
            return None
        
        # Actualizar campos si se proporcionan
        if data.title is not None:
            job.title = data.title
        if data.description is not None:
            job.description = data.description
        if data.department is not None:
            job.department = data.department
        if data.location is not None:
            job.location = data.location
        if data.seniority is not None:
            job.seniority = data.seniority
        if data.sector is not None:
            job.sector = data.sector
        if data.requirements is not None:
            job.requirements = data.requirements.model_dump()
        if data.salary_range_min is not None:
            job.salary_range_min = data.salary_range_min
        if data.salary_range_max is not None:
            job.salary_range_max = data.salary_range_max
        if data.employment_type is not None:
            job.employment_type = data.employment_type
        if data.status is not None:
            job.status = data.status
        if data.is_active is not None:
            job.is_active = data.is_active
        if data.assigned_consultant_id is not None:
            job.assigned_consultant_id = data.assigned_consultant_id
        
        job.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(job)
        
        return job
    
    async def delete_job(self, job_id: str) -> bool:
        """Eliminar oferta de trabajo."""
        job = await self.get_by_id(job_id)
        if not job:
            return False
        
        await self.db.delete(job)
        await self.db.flush()
        
        return True
    
    async def close_job(self, job_id: str) -> Optional[JobOpening]:
        """Cerrar oferta de trabajo."""
        return await self.update_job(
            job_id,
            JobOpeningUpdate(status=JobStatus.CLOSED.value, is_active=False)
        )
    
    async def get_job_candidates(
        self,
        job_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Candidate], int]:
        """Obtener candidatos de una oferta."""
        query = select(Candidate).where(Candidate.job_opening_id == job_id)
        
        if status:
            query = query.where(Candidate.status == status)
        
        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Ordenar y paginar
        query = query.order_by(desc(Candidate.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        candidates = result.scalars().all()
        
        return candidates, total
