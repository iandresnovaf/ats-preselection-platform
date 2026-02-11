"""Servicio para gestión de evaluaciones."""
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload

from app.models import Evaluation, Candidate


class EvaluationService:
    """Servicio para gestionar evaluaciones."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, evaluation_id: str) -> Optional[Evaluation]:
        """Obtener evaluación por ID."""
        result = await self.db.execute(
            select(Evaluation).where(Evaluation.id == evaluation_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id_with_candidate(self, evaluation_id: str) -> Optional[Evaluation]:
        """Obtener evaluación con su candidato."""
        result = await self.db.execute(
            select(Evaluation)
            .where(Evaluation.id == evaluation_id)
            .options(selectinload(Evaluation.candidate))
        )
        return result.scalar_one_or_none()
    
    async def list_evaluations(
        self,
        candidate_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Evaluation], int]:
        """Listar evaluaciones con filtros y paginación."""
        query = select(Evaluation)
        
        if candidate_id:
            query = query.where(Evaluation.candidate_id == candidate_id)
        
        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Ordenar y paginar
        query = query.order_by(desc(Evaluation.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        evaluations = result.scalars().all()
        
        return evaluations, total
    
    async def create_evaluation(
        self,
        candidate_id: str,
        score: float,
        decision: str,
        strengths: Optional[list] = None,
        gaps: Optional[list] = None,
        red_flags: Optional[list] = None,
        evidence: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        prompt_version: Optional[str] = None,
        evaluation_time_ms: Optional[int] = None,
    ) -> Evaluation:
        """Crear nueva evaluación."""
        evaluation = Evaluation(
            candidate_id=candidate_id,
            score=score,
            decision=decision,
            strengths=strengths or [],
            gaps=gaps or [],
            red_flags=red_flags or [],
            evidence=evidence,
            llm_provider=llm_provider,
            llm_model=llm_model,
            prompt_version=prompt_version,
            evaluation_time_ms=evaluation_time_ms,
        )
        
        self.db.add(evaluation)
        await self.db.flush()
        await self.db.refresh(evaluation)
        
        return evaluation
    
    async def delete_evaluation(self, evaluation_id: str) -> bool:
        """Eliminar evaluación."""
        evaluation = await self.get_by_id(evaluation_id)
        if not evaluation:
            return False
        
        await self.db.delete(evaluation)
        await self.db.flush()
        
        return True
    
    async def get_candidate_evaluations(self, candidate_id: str) -> List[Evaluation]:
        """Obtener todas las evaluaciones de un candidato."""
        result = await self.db.execute(
            select(Evaluation)
            .where(Evaluation.candidate_id == candidate_id)
            .order_by(desc(Evaluation.created_at))
        )
        return result.scalars().all()
    
    async def get_latest_evaluation(self, candidate_id: str) -> Optional[Evaluation]:
        """Obtener la evaluación más reciente de un candidato."""
        result = await self.db.execute(
            select(Evaluation)
            .where(Evaluation.candidate_id == candidate_id)
            .order_by(desc(Evaluation.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
