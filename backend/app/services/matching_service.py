"""Servicio de Matching IA entre Candidatos y Jobs.

Este servicio implementa el core de análisis de match usando IA,
con cache, manejo de errores graceful, y auditoría completa.
"""
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_
from sqlalchemy.orm import selectinload

# Configurar logger
logger = logging.getLogger(__name__)


class MatchingError(Exception):
    """Error base del servicio de matching."""
    pass


class CandidateNotFoundError(MatchingError):
    """Candidato no encontrado."""
    pass


class JobNotFoundError(MatchingError):
    """Job no encontrado."""
    pass


class CVNotParsedError(MatchingError):
    """CV del candidato no ha sido parseado."""
    pass


class OpenAIError(MatchingError):
    """Error de comunicación con OpenAI."""
    pass


class RateLimitError(MatchingError):
    """Límite de rate limiting alcanzado."""
    pass


class MatchingService:
    """Servicio para análisis de matching entre candidatos y jobs usando IA."""
    
    # Umbrales de recomendación
    THRESHOLD_PROCEED = 75.0  # Score > 75 = PROCEED
    THRESHOLD_REVIEW = 50.0   # Score 50-75 = REVIEW
    # Score < 50 = REJECT
    
    # Cache TTL (24 horas)
    CACHE_TTL_SECONDS = 86400
    
    # Timeout para análisis (5 segundos)
    ANALYSIS_TIMEOUT_SECONDS = 5
    
    def __init__(
        self, 
        db: AsyncSession,
        cache=None,
        openai_client=None,
        prompt_template: Optional[str] = None
    ):
        """
        Inicializa el servicio de matching.
        
        Args:
            db: Sesión de base de datos SQLAlchemy
            cache: Instancia de cache (opcional)
            openai_client: Cliente de OpenAI (opcional, se crea lazy)
            prompt_template: Template de prompt personalizado (opcional)
        """
        self.db = db
        self.cache = cache
        self._openai_client = openai_client
        self._prompt_template = prompt_template or self._get_default_prompt_template()
    
    def _get_openai_client(self):
        """Lazy load del cliente OpenAI."""
        if self._openai_client is None:
            try:
                import openai
                from app.core.config import settings
                
                api_key = settings.OPENAI_API_KEY
                if not api_key:
                    logger.warning("OPENAI_API_KEY no configurada")
                    return None
                
                self._openai_client = openai.AsyncOpenAI(api_key=api_key)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.error("openai package not installed")
                return None
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {e}")
                return None
        
        return self._openai_client
    
    def _get_default_prompt_template(self) -> str:
        """Retorna el template de prompt por defecto para análisis de matching."""
        return """Analiza este CV contra los requisitos del puesto y genera un análisis estructurado.

=== CV DEL CANDIDATO ===
{ cv_text }

=== REQUISITOS DEL PUESTO ===
Título: { job_title }
Descripción: { job_description }
Requisitos: { job_requirements }

Genera un análisis en formato JSON con la siguiente estructura:
{{
    "score": 85.5,  // Score general 0-100
    "skills_match": {{
        "required_skills_percentage": 80.0,
        "matched_skills": ["skill1", "skill2"],
        "missing_skills": ["skill3"],
        "extra_skills": ["skill4"]
    }},
    "experience_match": {{
        "years_found": 5,
        "years_required": 3,
        "match_percentage": 100.0
    }},
    "education_match": {{
        "match_percentage": 100.0,
        "details": "Descripción"
    }},
    "recommendation": "PROCEED",  // PROCEED (>75), REVIEW (50-75), REJECT (<50)
    "reasoning": "Explicación detallada del análisis",
    "strengths": ["Fortaleza 1", "Fortaleza 2"],
    "gaps": ["Gap 1", "Gap 2"],
    "red_flags": []  // Lista vacía si no hay, o items si existen
}}

Instrucciones:
1. Score > 75 = PROCEED (candidato recomendado)
2. Score 50-75 = REVIEW (requiere revisión manual)
3. Score < 50 = REJECT (no cumple requisitos)
4. Sé objetivo y basa el análisis solo en la información proporcionada
5. No inventes información que no esté en el CV"""
    
    def _sanitize_input(self, text: str, max_length: int = 10000) -> str:
        """
        Sanitiza input antes de enviar a OpenAI.
        
        Args:
            text: Texto a sanitizar
            max_length: Longitud máxima permitida
            
        Returns:
            Texto sanitizado
        """
        if not text:
            return ""
        
        # Limitar longitud
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        # Eliminar caracteres de control excepto newlines y tabs
        import re
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text.strip()
    
    def _compute_hash(self, data: Dict[str, Any]) -> str:
        """Computa hash SHA-256 de datos para versionado de cache."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _get_cache_key(self, candidate_id: str, job_id: str, cv_hash: str, job_hash: str) -> str:
        """Genera clave de cache única."""
        return f"matching:{candidate_id}:{job_id}:{cv_hash[:16]}:{job_hash[:16]}"
    
    async def _get_cached_result(
        self, 
        candidate_id: str, 
        job_id: str,
        cv_hash: str,
        job_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Intenta obtener resultado cacheado."""
        if not self.cache:
            return None
        
        try:
            cache_key = self._get_cache_key(candidate_id, job_id, cv_hash, job_hash)
            cached = await self.cache.get(cache_key)
            
            if cached:
                logger.info(f"Cache hit for matching {candidate_id}:{job_id}")
                return cached
        except Exception as e:
            logger.warning(f"Error reading from cache: {e}")
        
        return None
    
    async def _cache_result(
        self,
        candidate_id: str,
        job_id: str,
        cv_hash: str,
        job_hash: str,
        result: Dict[str, Any]
    ):
        """Guarda resultado en cache."""
        if not self.cache:
            return
        
        try:
            cache_key = self._get_cache_key(candidate_id, job_id, cv_hash, job_hash)
            await self.cache.set(cache_key, result, ttl=self.CACHE_TTL_SECONDS)
            logger.info(f"Cached matching result for {candidate_id}:{job_id}")
        except Exception as e:
            logger.warning(f"Error writing to cache: {e}")
    
    async def _get_candidate_with_cv(self, candidate_id: str) -> Tuple[Any, str]:
        """
        Obtiene candidato con su CV parseado.
        
        Args:
            candidate_id: ID del candidato
            
        Returns:
            Tupla (candidato, cv_text)
            
        Raises:
            CandidateNotFoundError: Si el candidato no existe
            CVNotParsedError: Si el CV no ha sido parseado
        """
        from app.models import Candidate
        from app.models.rhtools import DocumentTextExtraction
        
        result = await self.db.execute(
            select(Candidate)
            .where(Candidate.id == candidate_id)
            .options(selectinload(Candidate.documents))
        )
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            raise CandidateNotFoundError(f"Candidato {candidate_id} no encontrado")
        
        # Obtener texto del CV
        cv_text = ""
        
        # Primero intentar con extracted_data del candidato
        if candidate.raw_data:
            cv_text = json.dumps(candidate.raw_data, default=str)
        
        # Si hay documentos, buscar el texto extraído
        if candidate.documents:
            for doc in candidate.documents:
                if doc.document_type in ['resume', 'cv']:
                    # Buscar extracción de texto
                    extraction_result = await self.db.execute(
                        select(DocumentTextExtraction)
                        .where(DocumentTextExtraction.document_id == doc.id)
                    )
                    extraction = extraction_result.scalar_one_or_none()
                    
                    if extraction and extraction.extracted_text:
                        cv_text = extraction.extracted_text
                        break
        
        if not cv_text:
            # Fallback: usar datos estructurados si existen
            cv_parts = []
            if candidate.full_name:
                cv_parts.append(f"Nombre: {candidate.full_name}")
            if candidate.extracted_skills:
                cv_parts.append(f"Skills: {', '.join(candidate.extracted_skills)}")
            if candidate.extracted_experience:
                cv_parts.append(f"Experiencia: {json.dumps(candidate.extracted_experience)}")
            if candidate.extracted_education:
                cv_parts.append(f"Educación: {json.dumps(candidate.extracted_education)}")
            
            cv_text = "\n".join(cv_parts) if cv_parts else ""
        
        if not cv_text:
            raise CVNotParsedError(f"CV del candidato {candidate_id} no disponible o no parseado")
        
        return candidate, cv_text
    
    async def _get_job_with_requirements(self, job_id: str) -> Tuple[Any, Dict[str, Any]]:
        """
        Obtiene job con sus requisitos.
        
        Args:
            job_id: ID del job
            
        Returns:
            Tupla (job, requirements_dict)
            
        Raises:
            JobNotFoundError: Si el job no existe
        """
        from app.models import JobOpening
        
        result = await self.db.execute(
            select(JobOpening)
            .where(JobOpening.id == job_id)
            .options(selectinload(JobOpening.job_description_document))
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise JobNotFoundError(f"Job {job_id} no encontrado")
        
        # Construir requisitos
        requirements = job.requirements or {}
        
        # Si hay documento PDF del JD, extraer texto
        job_description_text = job.description or ""
        if job.job_description_document:
            from app.models.rhtools import DocumentTextExtraction
            extraction_result = await self.db.execute(
                select(DocumentTextExtraction)
                .where(DocumentTextExtraction.document_id == job.job_description_document.id)
            )
            extraction = extraction_result.scalar_one_or_none()
            if extraction and extraction.extracted_text:
                job_description_text = extraction.extracted_text
        
        return job, {
            "title": job.title,
            "description": job_description_text,
            "requirements": requirements,
            "seniority": job.seniority,
            "department": job.department,
            "location": job.location,
            "employment_type": job.employment_type,
        }
    
    def _determine_recommendation(self, score: float) -> str:
        """Determina la recomendación basada en el score."""
        if score >= self.THRESHOLD_PROCEED:
            return "PROCEED"
        elif score >= self.THRESHOLD_REVIEW:
            return "REVIEW"
        else:
            return "REJECT"
    
    async def analyze_match(
        self,
        candidate_id: str,
        job_id: str,
        user_id: Optional[str] = None,
        force_refresh: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analiza el match entre un candidato y un job.
        
        Args:
            candidate_id: ID del candidato
            job_id: ID del job
            user_id: ID del usuario que solicita el análisis (para auditoría)
            force_refresh: Si es True, ignora el cache
            ip_address: IP del request (para auditoría)
            user_agent: User agent (para auditoría)
            
        Returns:
            Dict con el resultado del matching
            
        Raises:
            CandidateNotFoundError: Si el candidato no existe
            JobNotFoundError: Si el job no existe
            CVNotParsedError: Si el CV no está parseado
            OpenAIError: Si hay error con OpenAI
        """
        start_time = time.time()
        
        try:
            # 1. Obtener datos del candidato y job
            candidate, cv_text = await self._get_candidate_with_cv(candidate_id)
            job, job_requirements = await self._get_job_with_requirements(job_id)
            
            # 2. Verificar permisos (el job debe ser accesible)
            # Nota: La validación de permisos se hace en el endpoint
            
            # 3. Calcular hashes para cache
            cv_hash = self._compute_hash({"text": cv_text, "skills": candidate.extracted_skills})
            job_hash = self._compute_hash(job_requirements)
            
            # 4. Verificar cache (si no es force_refresh)
            if not force_refresh:
                cached_result = await self._get_cached_result(candidate_id, job_id, cv_hash, job_hash)
                if cached_result:
                    # Registrar uso de cache en auditoría
                    await self._log_audit(
                        action="ANALYZE_CACHED",
                        candidate_id=candidate_id,
                        job_id=job_id,
                        user_id=user_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=True,
                        processing_time_ms=int((time.time() - start_time) * 1000)
                    )
                    return cached_result
            
            # 5. Preparar prompt
            prompt = self._prompt_template.format(
                cv_text=self._sanitize_input(cv_text, max_length=8000),
                job_title=self._sanitize_input(job_requirements["title"]),
                job_description=self._sanitize_input(job_requirements["description"], max_length=3000),
                job_requirements=self._sanitize_input(json.dumps(job_requirements["requirements"]), max_length=2000)
            )
            
            # 6. Llamar a OpenAI
            client = self._get_openai_client()
            
            if not client:
                # Fallback: Usar análisis local simple si no hay OpenAI
                logger.warning("OpenAI not available, using fallback analysis")
                result = await self._fallback_analysis(candidate, job_requirements)
            else:
                result = await self._call_openai(prompt)
            
            # 7. Procesar resultado
            result["candidate_id"] = str(candidate_id)
            result["job_id"] = str(job_id)
            result["analyzed_at"] = datetime.utcnow().isoformat()
            result["is_cached"] = False
            
            # 8. Guardar en BD
            await self._save_match_result(
                candidate_id=candidate_id,
                job_id=job_id,
                result=result,
                user_id=user_id,
                cv_hash=cv_hash,
                job_hash=job_hash
            )
            
            # 9. Guardar en cache
            await self._cache_result(candidate_id, job_id, cv_hash, job_hash, result)
            
            # 10. Registrar auditoría
            processing_time = int((time.time() - start_time) * 1000)
            await self._log_audit(
                action="ANALYZE",
                candidate_id=candidate_id,
                job_id=job_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
                processing_time_ms=processing_time
            )
            
            return result
            
        except (CandidateNotFoundError, JobNotFoundError, CVNotParsedError):
            raise
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            await self._log_audit(
                action="ANALYZE",
                candidate_id=candidate_id,
                job_id=job_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                error_message=str(e),
                processing_time_ms=processing_time
            )
            raise OpenAIError(f"Error en análisis de matching: {str(e)}")
    
    async def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """
        Llama a OpenAI para obtener el análisis.
        
        Args:
            prompt: Prompt completo
            
        Returns:
            Dict con el resultado parseado
        """
        client = self._get_openai_client()
        
        if not client:
            raise OpenAIError("OpenAI client not available")
        
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",  # Modelo eficiente para este análisis
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en reclutamiento técnico. Analiza CVs contra requisitos de puestos de forma objetiva. Responde SOLO con JSON válido."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,  # Máxima determinidad
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Validar y normalizar resultado
            return self._normalize_result(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from OpenAI: {e}")
            raise OpenAIError(f"Respuesta inválida de OpenAI: {e}")
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise OpenAIError(f"Error de OpenAI: {e}")
    
    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza y valida el resultado de OpenAI."""
        normalized = {
            "score": float(result.get("score", 0)),
            "match_details": result.get("skills_match", {}),
            "recommendation": result.get("recommendation", "REVIEW"),
            "reasoning": result.get("reasoning", ""),
            "strengths": result.get("strengths", []),
            "gaps": result.get("gaps", []),
            "red_flags": result.get("red_flags", []),
            "experience_match": result.get("experience_match", {}),
            "education_match": result.get("education_match", {}),
        }
        
        # Validar score
        normalized["score"] = max(0, min(100, normalized["score"]))
        
        # Validar recomendación
        valid_recommendations = ["PROCEED", "REVIEW", "REJECT"]
        if normalized["recommendation"] not in valid_recommendations:
            normalized["recommendation"] = self._determine_recommendation(normalized["score"])
        
        return normalized
    
    async def _fallback_analysis(
        self,
        candidate: Any,
        job_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Análisis fallback cuando OpenAI no está disponible.
        Usa matching simple basado en skills.
        """
        required_skills = job_requirements.get("requirements", {}).get("required_skills", [])
        candidate_skills = candidate.extracted_skills or []
        
        if not required_skills:
            score = 50.0  # Sin requisitos claros, score neutral
        else:
            # Matching simple de skills
            matched = [s for s in required_skills if any(
                s.lower() in cs.lower() or cs.lower() in s.lower() 
                for cs in candidate_skills
            )]
            score = (len(matched) / len(required_skills)) * 100
        
        return {
            "score": score,
            "match_details": {
                "required_skills_percentage": score,
                "matched_skills": [],
                "missing_skills": required_skills,
                "extra_skills": candidate_skills
            },
            "experience_match": {
                "years_found": 0,
                "years_required": job_requirements.get("requirements", {}).get("min_years_experience", 0),
                "match_percentage": 0
            },
            "education_match": {
                "match_percentage": 0,
                "details": "Análisis no disponible (fallback mode)"
            },
            "recommendation": self._determine_recommendation(score),
            "reasoning": "Análisis generado en modo fallback (OpenAI no disponible). Basado solo en matching de skills.",
            "strengths": [],
            "gaps": ["Análisis completo no disponible"],
            "red_flags": [],
            "llm_provider": "fallback",
            "llm_model": "simple-skill-matching",
            "prompt_version": "fallback"
        }
    
    async def _save_match_result(
        self,
        candidate_id: str,
        job_id: str,
        result: Dict[str, Any],
        user_id: Optional[str],
        cv_hash: str,
        job_hash: str
    ):
        """Guarda el resultado del matching en la base de datos."""
        from app.models.match_result import MatchResult, MatchRecommendation
        
        match_result = MatchResult(
            candidate_id=candidate_id,
            job_opening_id=job_id,
            score=result["score"],
            match_details=result.get("match_details", {}),
            recommendation=result["recommendation"],
            reasoning=result.get("reasoning", ""),
            strengths=result.get("strengths", []),
            gaps=result.get("gaps", []),
            red_flags=result.get("red_flags", []),
            llm_provider=result.get("llm_provider", "openai"),
            llm_model=result.get("llm_model", "gpt-4o-mini"),
            prompt_version=result.get("prompt_version", "v1.0"),
            analyzed_by=user_id,
            cv_version_hash=cv_hash,
            job_version_hash=job_hash,
            cache_expires_at=datetime.utcnow() + timedelta(seconds=self.CACHE_TTL_SECONDS)
        )
        
        self.db.add(match_result)
        await self.db.flush()
        await self.db.refresh(match_result)
        
        result["match_result_id"] = str(match_result.id)
    
    async def _log_audit(
        self,
        action: str,
        candidate_id: Optional[str] = None,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ):
        """Registra entrada de auditoría."""
        from app.models.match_result import MatchingAuditLog
        
        # No bloquear si falla el logging
        try:
            audit = MatchingAuditLog(
                action=action,
                candidate_id=candidate_id,
                job_opening_id=job_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success="Y" if success else "N",
                error_message=error_message,
                processing_time_ms=processing_time_ms
            )
            self.db.add(audit)
            await self.db.flush()
        except Exception as e:
            logger.error(f"Error logging audit: {e}")
    
    async def get_best_jobs_for_candidate(
        self,
        candidate_id: str,
        limit: int = 10,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los mejores jobs para un candidato.
        
        Args:
            candidate_id: ID del candidato
            limit: Cantidad máxima de resultados
            min_score: Score mínimo para incluir
            
        Returns:
            Lista de jobs con sus scores de matching
        """
        from app.models import JobOpening, MatchResult
        
        # Primero buscar matches existentes
        result = await self.db.execute(
            select(MatchResult, JobOpening)
            .join(JobOpening, MatchResult.job_opening_id == JobOpening.id)
            .where(
                and_(
                    MatchResult.candidate_id == candidate_id,
                    MatchResult.score >= min_score
                )
            )
            .order_by(desc(MatchResult.score))
            .limit(limit)
        )
        
        matches = result.all()
        
        return [
            {
                "job_id": str(match.JobOpening.id),
                "job_title": match.JobOpening.title,
                "department": match.JobOpening.department,
                "location": match.JobOpening.location,
                "score": match.MatchResult.score,
                "recommendation": match.MatchResult.recommendation,
                "analyzed_at": match.MatchResult.analyzed_at.isoformat() if match.MatchResult.analyzed_at else None
            }
            for match in matches
        ]
    
    async def get_best_candidates_for_job(
        self,
        job_id: str,
        limit: int = 20,
        min_score: float = 0.0,
        recommendation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los mejores candidatos para un job.
        
        Args:
            job_id: ID del job
            limit: Cantidad máxima de resultados
            min_score: Score mínimo para incluir
            recommendation: Filtrar por recomendación específica (PROCEED, REVIEW, REJECT)
            
        Returns:
            Lista de candidatos con sus scores de matching
        """
        from app.models import Candidate, MatchResult
        
        query = (
            select(MatchResult, Candidate)
            .join(Candidate, MatchResult.candidate_id == Candidate.id)
            .where(
                and_(
                    MatchResult.job_opening_id == job_id,
                    MatchResult.score >= min_score
                )
            )
            .order_by(desc(MatchResult.score))
            .limit(limit)
        )
        
        if recommendation:
            query = query.where(MatchResult.recommendation == recommendation)
        
        result = await self.db.execute(query)
        matches = result.all()
        
        return [
            {
                "candidate_id": str(match.Candidate.id),
                "full_name": match.Candidate.full_name,
                "email": match.Candidate.email,
                "score": match.MatchResult.score,
                "recommendation": match.MatchResult.recommendation,
                "strengths": match.MatchResult.strengths,
                "gaps": match.MatchResult.gaps,
                "analyzed_at": match.MatchResult.analyzed_at.isoformat() if match.MatchResult.analyzed_at else None
            }
            for match in matches
        ]
    
    async def batch_analyze(
        self,
        candidate_ids: List[str],
        job_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analiza múltiples candidatos contra un job.
        
        Args:
            candidate_ids: Lista de IDs de candidatos
            job_id: ID del job
            user_id: ID del usuario que solicita el análisis
            
        Returns:
            Lista de resultados de matching
        """
        results = []
        
        for candidate_id in candidate_ids:
            try:
                result = await self.analyze_match(
                    candidate_id=candidate_id,
                    job_id=job_id,
                    user_id=user_id
                )
                results.append({
                    "candidate_id": candidate_id,
                    "success": True,
                    "result": result
                })
            except Exception as e:
                results.append({
                    "candidate_id": candidate_id,
                    "success": False,
                    "error": str(e)
                })
        
        return results
