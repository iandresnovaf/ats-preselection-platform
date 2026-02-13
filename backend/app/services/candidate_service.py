"""Servicio para gestión de candidatos."""
from typing import List, Optional, Dict, Any
from datetime import datetime
import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload, joinedload

from app.models import Candidate, CandidateStatus, Evaluation, JobOpening
from app.schemas import CandidateCreate, CandidateUpdate
from app.services.evaluation_service import EvaluationService
from app.core.llm_cache import get_cached_evaluation, cache_evaluation
from app.integrations.llm import LLMClient, EvaluationResult


class CandidateService:
    """Servicio para gestionar candidatos."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.evaluation_service = EvaluationService(db)
    
    async def get_by_id(self, candidate_id: str) -> Optional[Candidate]:
        """Obtener candidato por ID."""
        result = await self.db.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id_with_evaluations(self, candidate_id: str) -> Optional[Candidate]:
        """Obtener candidato con sus evaluaciones en un solo query usando JOIN."""
        result = await self.db.execute(
            select(Candidate)
            .options(joinedload(Candidate.evaluations))
            .where(Candidate.id == candidate_id)
        )
        return result.scalar_one_or_none()
    
    async def list_candidates(
        self,
        job_opening_id: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Candidate], int]:
        """Listar candidatos con filtros y paginación."""
        query = select(Candidate)
        
        # Aplicar filtros
        filters = []
        if job_opening_id:
            filters.append(Candidate.job_opening_id == job_opening_id)
        if status:
            filters.append(Candidate.status == status)
        if source:
            filters.append(Candidate.source == source)
        if search:
            search_filter = or_(
                Candidate.full_name.ilike(f"%{search}%"),
                Candidate.email.ilike(f"%{search}%"),
            )
            filters.append(search_filter)
        
        if filters:
            query = query.where(and_(*filters))
        
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
    
    async def create_candidate(self, data: CandidateCreate) -> Candidate:
        """Crear nuevo candidato."""
        # Extraer datos del schema o del raw_data
        raw_data = data.raw_data or {}
        
        # Priorizar datos directos del schema sobre raw_data
        full_name = data.full_name or raw_data.get("full_name") or raw_data.get("name", "")
        email = data.email or raw_data.get("email", "")
        phone = data.phone or raw_data.get("phone", "")
        
        # Extraer skills, experiencia y educación
        extracted_skills = data.extracted_skills or raw_data.get("skills", [])
        extracted_experience = data.extracted_experience or raw_data.get("experience", [])
        extracted_education = data.extracted_education or raw_data.get("education", [])
        
        # Normalizar email y teléfono para anti-duplicados
        email_normalized = email.lower().strip() if email else None
        phone_normalized = self._normalize_phone(phone) if phone else None
        
        candidate = Candidate(
            job_opening_id=data.job_opening_id,
            email=email,
            phone=phone,
            full_name=full_name,
            email_normalized=email_normalized,
            phone_normalized=phone_normalized,
            raw_data=raw_data,
            extracted_skills=extracted_skills,
            extracted_experience=extracted_experience,
            extracted_education=extracted_education,
            status=CandidateStatus.NEW.value,
            source=data.source,
        )
        
        self.db.add(candidate)
        await self.db.flush()
        await self.db.refresh(candidate)
        
        return candidate
    
    async def update_candidate(
        self, 
        candidate_id: str, 
        data: CandidateUpdate
    ) -> Optional[Candidate]:
        """Actualizar candidato."""
        candidate = await self.get_by_id(candidate_id)
        if not candidate:
            return None
        
        # Actualizar campos si se proporcionan
        if data.status is not None:
            candidate.status = data.status
        if data.email is not None:
            candidate.email = data.email
            candidate.email_normalized = data.email.lower().strip()
        if data.phone is not None:
            candidate.phone = data.phone
            candidate.phone_normalized = self._normalize_phone(data.phone)
        if data.full_name is not None:
            candidate.full_name = data.full_name
        
        candidate.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(candidate)
        
        return candidate
    
    async def change_status(
        self, 
        candidate_id: str, 
        new_status: str
    ) -> Optional[Candidate]:
        """Cambiar estado del candidato."""
        return await self.update_candidate(
            candidate_id,
            CandidateUpdate(status=new_status)
        )
    
    async def evaluate_candidate(
        self,
        candidate_id: str,
        job_opening: JobOpening,
        llm_config: Dict[str, Any],
        force_refresh: bool = False,
    ) -> Evaluation:
        """
        Evaluar candidato con LLM.
        
        Args:
            candidate_id: ID del candidato
            job_opening: Objeto JobOpening
            llm_config: Configuración del LLM
            force_refresh: Si es True, ignora el caché
        
        Returns:
            Evaluation: Objeto de evaluación creado
        """
        # Obtener candidato
        candidate = await self.get_by_id(candidate_id)
        if not candidate:
            raise ValueError("Candidato no encontrado")
        
        # Preparar datos para el LLM
        candidate_data = {
            "id": str(candidate.id),
            "full_name": candidate.full_name,
            "email": candidate.email,
            "extracted_skills": candidate.extracted_skills or [],
            "extracted_experience": candidate.extracted_experience or [],
            "extracted_education": candidate.extracted_education or [],
            "raw_data": candidate.raw_data or {},
        }
        
        job_data = {
            "id": str(job_opening.id),
            "title": job_opening.title,
            "description": job_opening.description,
            "department": job_opening.department,
            "location": job_opening.location,
            "seniority": job_opening.seniority,
        }
        
        provider = llm_config.get("provider", "openai")
        model = llm_config.get("model", "gpt-4o-mini")
        
        # Verificar caché
        start_time = time.time()
        cached_result = None
        
        if not force_refresh:
            cached_result = await get_cached_evaluation(
                candidate_data=candidate_data,
                job_data=job_data,
                provider=provider,
                model=model,
            )
        
        if cached_result:
            # Usar resultado cacheado
            result = {
                "score": cached_result["score"],
                "decision": cached_result["decision"],
                "strengths": cached_result.get("strengths", []),
                "gaps": cached_result.get("gaps", []),
                "red_flags": cached_result.get("red_flags", []),
                "evidence": cached_result.get("evidence", ""),
                "cached": True,
            }
            evaluation_time_ms = int((time.time() - start_time) * 1000)
        else:
            # Llamar al LLM
            llm_client = LLMClient(config=None)
            await llm_client.initialize(self.db)
            
            try:
                eval_result: EvaluationResult = await llm_client.evaluate_candidate(
                    candidate_data=candidate_data,
                    job_data=job_data,
                )
                
                result = {
                    "score": eval_result.score,
                    "decision": eval_result.decision.upper(),  # Convertir a nuestro formato
                    "strengths": eval_result.strengths,
                    "gaps": eval_result.gaps,
                    "red_flags": eval_result.red_flags,
                    "evidence": eval_result.evidence,
                    "cached": False,
                }
                
                # Guardar en caché
                await cache_evaluation(
                    candidate_data=candidate_data,
                    job_data=job_data,
                    result=result,
                    provider=provider,
                    model=model,
                    ttl=86400,  # 24 horas
                )
                
            except Exception as e:
                # Fallback graceful
                result = {
                    "score": 50.0,
                    "decision": "REVIEW",
                    "strengths": [],
                    "gaps": ["Error en evaluación automática"],
                    "red_flags": [],
                    "evidence": f"Error durante evaluación: {str(e)}. Revisión manual requerida.",
                    "cached": False,
                    "error": True,
                }
            finally:
                await llm_client.close()
            
            evaluation_time_ms = int((time.time() - start_time) * 1000)
        
        # Crear evaluación en BD
        evaluation = await self.evaluation_service.create_evaluation(
            candidate_id=candidate_id,
            score=result["score"],
            decision=result["decision"],
            strengths=result["strengths"],
            gaps=result["gaps"],
            red_flags=result["red_flags"],
            evidence=result["evidence"],
            llm_provider=provider,
            llm_model=model,
            prompt_version=llm_config.get("prompt_version", "v1.0"),
            evaluation_time_ms=evaluation_time_ms,
        )
        
        # Actualizar estado del candidato
        await self.change_status(candidate_id, CandidateStatus.EVALUATION.value)
        
        return evaluation
    
    async def check_duplicates(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        job_opening_id: Optional[str] = None,
    ) -> List[Candidate]:
        """Verificar candidatos duplicados."""
        query = select(Candidate).where(Candidate.is_duplicate == False)
        
        filters = []
        if email:
            filters.append(Candidate.email_normalized == email.lower().strip())
        if phone:
            filters.append(Candidate.phone_normalized == self._normalize_phone(phone))
        if job_opening_id:
            filters.append(Candidate.job_opening_id == job_opening_id)
        
        if filters:
            query = query.where(or_(*filters))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalizar número de teléfono para comparación."""
        if not phone:
            return ""
        # Remover caracteres no numéricos
        return ''.join(c for c in phone if c.isdigit())
