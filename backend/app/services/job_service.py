"""Servicio para gestión de ofertas de trabajo."""
from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models import JobOpening, JobStatus, Candidate
from app.schemas import JobOpeningCreate, JobOpeningUpdate


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
    
    async def create_job(self, data: JobOpeningCreate) -> JobOpening:
        """Crear nueva oferta de trabajo."""
        job = JobOpening(
            title=data.title,
            description=data.description,
            department=data.department,
            location=data.location,
            seniority=data.seniority,
            sector=data.sector,
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
