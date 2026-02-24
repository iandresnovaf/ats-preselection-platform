"""
Scoring Service - Evaluación de compatibilidad candidato-vacante usando IA.

Este servicio utiliza LLM (OpenAI/Claude) para evaluar la compatibilidad
entre un CV de candidato y los requisitos de una vacante.
"""
import json
import os
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select

from app.models.core_ats import (
    HHApplication, HHCandidate, HHRole, HHClient,
    HHCVExtraction, HHDocument, HHAuditLog, ScoringStatus
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScoringResult:
    """Resultado de la evaluación de compatibilidad."""
    def __init__(
        self,
        score: float,
        justification: str,
        skill_match: Dict[str, Any],
        experience_match: Dict[str, Any],
        seniority_match: Dict[str, Any],
        industry_match: Optional[Dict[str, Any]] = None,
        recommendations: Optional[list] = None
    ):
        self.score = score
        self.justification = justification
        self.skill_match = skill_match
        self.experience_match = experience_match
        self.seniority_match = seniority_match
        self.industry_match = industry_match or {}
        self.recommendations = recommendations or []


class ScoringService:
    """Servicio para evaluar compatibilidad candidato-vacante usando IA."""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    async def score_application(
        self,
        application_id: str,
        db: AsyncSession,
        current_user: Optional[str] = None
    ) -> ScoringResult:
        """
        Evalúa la compatibilidad entre un candidato y una vacante.
        
        Args:
            application_id: ID de la aplicación
            db: Sesión de base de datos
            current_user: Usuario que ejecuta la acción
            
        Returns:
            ScoringResult con el score y justificación
        """
        # 1. Obtener la aplicación con todas las relaciones
        result = await db.execute(
            select(HHApplication)
            .options(
                joinedload(HHApplication.candidate),
                joinedload(HHApplication.role).joinedload(HHRole.client)
            )
            .filter(HHApplication.application_id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            raise ValueError(f"Aplicación {application_id} no encontrada")
        
        # Marcar como en procesamiento
        application.scoring_status = ScoringStatus.PROCESSING
        await db.commit()
        
        try:
            candidate = application.candidate
            role = application.role
            
            # 2. Obtener datos del CV extraídos
            cv_data = await self._get_cv_data(candidate.candidate_id, db)
            
            # 3. Obtener descripción del rol
            role_data = await self._get_role_data(role, db)
            
            # 4. Generar evaluación con IA
            scoring_result = await self._evaluate_with_ai(
                cv_data=cv_data,
                role_data=role_data,
                candidate=candidate,
                role=role
            )
            
            # 5. Guardar el score en la aplicación
            application.overall_score = Decimal(str(scoring_result.score))
            application.scoring_status = ScoringStatus.COMPLETED
            application.scoring_error = None
            await db.commit()
            
            # 6. Crear registro de auditoría
            await self._log_scoring_event(
                application_id=application_id,
                score=scoring_result.score,
                justification=scoring_result.justification,
                changed_by=current_user or "system",
                db=db
            )
            
            return scoring_result
            
        except Exception as e:
            # Marcar como fallido
            application.scoring_status = ScoringStatus.FAILED
            application.scoring_error = str(e)[:500]  # Limitar longitud
            await db.commit()
            raise
    
    async def _get_cv_data(
        self,
        candidate_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Obtiene los datos del CV del candidato."""
        # Buscar en hh_cv_extractions (más reciente primero)
        result = await db.execute(
            select(HHCVExtraction)
            .filter(HHCVExtraction.candidate_id == candidate_id)
            .order_by(HHCVExtraction.created_at.desc())
            .limit(1)
        )
        extraction = result.scalar_one_or_none()
        
        if extraction and extraction.extracted_json:
            return {
                "raw_text": extraction.raw_text or "",
                "structured_data": extraction.extracted_json,
                "extraction_confidence": float(extraction.confidence_score) if extraction.confidence_score else None,
                "source": "cv_extraction"
            }
        
        # Si no hay extracción, buscar en documentos
        result = await db.execute(
            select(HHDocument)
            .filter(
                HHDocument.candidate_id == candidate_id,
                HHDocument.doc_type == "cv"
            )
            .order_by(HHDocument.uploaded_at.desc())
            .limit(1)
        )
        document = result.scalar_one_or_none()
        
        if document:
            return {
                "filename": document.original_filename,
                "source": "document",
                "document_id": str(document.document_id)
            }
        
        # Datos básicos del candidato
        result = await db.execute(
            select(HHCandidate).filter(HHCandidate.candidate_id == candidate_id)
        )
        candidate = result.scalar_one()
        
        return {
            "full_name": candidate.full_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "location": candidate.location,
            "linkedin_url": candidate.linkedin_url,
            "source": "basic_info"
        }
    
    async def _get_role_data(
        self,
        role: HHRole,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Obtiene los datos de la vacante."""
        role_data = {
            "role_id": str(role.role_id),
            "title": role.role_title,
            "location": role.location,
            "seniority": role.seniority,
            "client": role.client.client_name if role.client else None,
            "industry": role.client.industry if role.client else None,
        }
        
        # Si hay un documento de descripción del rol, intentar obtenerlo
        if role.role_description_doc_id:
            result = await db.execute(
                select(HHDocument).filter(
                    HHDocument.document_id == role.role_description_doc_id
                )
            )
            doc = result.scalar_one_or_none()
            if doc:
                role_data["description_doc"] = doc.original_filename
        
        return role_data
    
    async def _evaluate_with_ai(
        self,
        cv_data: Dict[str, Any],
        role_data: Dict[str, Any],
        candidate: HHCandidate,
        role: HHRole
    ) -> ScoringResult:
        """Evalúa la compatibilidad usando LLM."""
        
        # Construir el prompt
        prompt = self._build_scoring_prompt(cv_data, role_data, candidate, role)
        
        # Llamar a la API de OpenAI
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.openai_api_key)
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en reclutamiento y selección de talento. Tu tarea es evaluar la compatibilidad entre candidatos y vacantes de manera objetiva y profesional. Responde únicamente en formato JSON válido."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parsear la respuesta
            content = response.choices[0].message.content
            result = json.loads(content)
            
            return ScoringResult(
                score=float(result.get("score", 0)),
                justification=result.get("justification", "Sin justificación"),
                skill_match=result.get("skill_match", {}),
                experience_match=result.get("experience_match", {}),
                seniority_match=result.get("seniority_match", {}),
                industry_match=result.get("industry_match"),
                recommendations=result.get("recommendations", [])
            )
            
        except Exception as e:
            # Fallback: evaluación básica si falla la IA
            return await self._fallback_evaluation(cv_data, role_data, candidate, role, str(e))
    
    def _build_scoring_prompt(
        self,
        cv_data: Dict[str, Any],
        role_data: Dict[str, Any],
        candidate: HHCandidate,
        role: HHRole
    ) -> str:
        """Construye el prompt para la evaluación de IA."""
        
        # Extraer información del CV
        cv_text = ""
        structured = cv_data.get("structured_data", {})
        
        if cv_data.get("raw_text"):
            cv_text = cv_data["raw_text"][:3000]  # Limitar a 3000 chars
        elif structured:
            # Construir texto desde datos estructurados
            cv_parts = []
            
            if structured.get("full_name"):
                cv_parts.append(f"Nombre: {structured['full_name']}")
            if structured.get("headline"):
                cv_parts.append(f"Título: {structured['headline']}")
            if structured.get("summary"):
                cv_parts.append(f"Resumen: {structured['summary']}")
            if structured.get("years_experience"):
                cv_parts.append(f"Años de experiencia: {structured['years_experience']}")
            
            if structured.get("experiences"):
                cv_parts.append("\nExperiencia Laboral:")
                for exp in structured["experiences"][:5]:  # Limitar a 5 experiencias
                    cv_parts.append(f"- {exp.get('position', 'N/A')} en {exp.get('company', 'N/A')}")
                    if exp.get("description"):
                        cv_parts.append(f"  {exp['description'][:200]}...")
            
            if structured.get("skills"):
                skills = [s.get("name", "") for s in structured["skills"]]
                cv_parts.append(f"\nHabilidades: {', '.join(skills[:20])}")
            
            if structured.get("education"):
                cv_parts.append("\nEducación:")
                for edu in structured["education"][:3]:
                    cv_parts.append(f"- {edu.get('degree', 'N/A')} en {edu.get('institution', 'N/A')}")
            
            cv_text = "\n".join(cv_parts)
        
        # Información básica del candidato
        candidate_info = f"""
CANDIDATO:
- Nombre: {candidate.full_name}
- Ubicación: {candidate.location or 'No especificada'}
- LinkedIn: {candidate.linkedin_url or 'No proporcionado'}
"""
        
        # Información de la vacante
        role_info = f"""
VACANTE:
- Título: {role.role_title}
- Nivel: {role.seniority or 'No especificado'}
- Ubicación: {role.location or 'No especificada'}
- Cliente: {role_data.get('client', 'No especificado')}
- Industria: {role_data.get('industry', 'No especificada')}
"""
        
        prompt = f"""Evalúa la compatibilidad entre el siguiente candidato y la vacante. Proporciona un score del 0 al 100 y una justificación detallada.

{candidate_info}

CONTENIDO DEL CV:
{cv_text}

{role_info}

INSTRUCCIONES DE EVALUACIÓN:

1. MATCH DE SKILLS TÉCNICAS (30% del score):
   - Compara las habilidades del CV con las típicas requeridas para el rol
   - Identifica skills faltantes críticas vs. deseables
   - Evalúa la profundidad de conocimiento demostrada

2. AÑOS DE EXPERIENCIA (25% del score):
   - Compara años de experiencia del candidato vs. requisitos típicos del nivel
   - Evalúa relevancia de la experiencia previa
   - Considera progresión de carrera

3. NIVEL DE SENIORITY (25% del score):
   - Evalúa si el nivel del candidato coincide con {role.seniority or 'el nivel requerido'}
   - Considera responsabilidades previas vs. las esperadas
   - Analiza títulos de trabajo anteriores

4. INDUSTRIA/SECTOR (20% del score):
   - Evalúa experiencia en industria {role_data.get('industry', 'similar')} o relacionadas
   - Considera transferibilidad de skills entre industrias
   - Valora conocimiento de negocio específico

REGLAS IMPORTANTES:
- Score 90-100: Candidato ideal, cumple todos los requisitos
- Score 70-89: Candidato fuerte, cumple la mayoría de requisitos
- Score 50-69: Candidato aceptable, cumple algunos requisitos con potencial
- Score 30-49: Candidato débil, cumple pocos requisitos
- Score 0-29: Candidato no compatible

Responde EXACTAMENTE en este formato JSON:
{{
    "score": <número entre 0-100>,
    "justification": "<explicación detallada de 3-5 oraciones justificando el score>",
    "skill_match": {{
        "score": <0-100>,
        "matched_skills": ["skill1", "skill2"],
        "missing_skills": ["skill3"],
        "analysis": "<análisis del match de skills>"
    }},
    "experience_match": {{
        "score": <0-100>,
        "years_candidate": <número>,
        "years_required": <número o "No especificado">,
        "analysis": "<análisis de la experiencia>"
    }},
    "seniority_match": {{
        "score": <0-100>,
        "candidate_level": "<junior|mid|senior|lead|executive>",
        "required_level": "{role.seniority or 'No especificado'}",
        "analysis": "<análisis del nivel>"
    }},
    "industry_match": {{
        "score": <0-100>,
        "candidate_industries": ["industria1", "industria2"],
        "target_industry": "{role_data.get('industry', 'No especificada')}",
        "analysis": "<análisis de la industria>"
    }},
    "recommendations": [
        "<recomendación 1>",
        "<recomendación 2>"
    ]
}}"""
        
        return prompt
    
    async def _fallback_evaluation(
        self,
        cv_data: Dict[str, Any],
        role_data: Dict[str, Any],
        candidate: HHCandidate,
        role: HHRole,
        error_message: str
    ) -> ScoringResult:
        """Evaluación básica si falla la IA."""
        
        structured = cv_data.get("structured_data", {})
        
        # Calcular años de experiencia
        years_exp = structured.get("years_experience", 0)
        if not years_exp and structured.get("experiences"):
            years_exp = len(structured["experiences"]) * 2  # Estimación básica
        
        # Match básico de seniority
        seniority_score = 50
        candidate_title = structured.get("headline", "")
        role_seniority = (role.seniority or "").lower()
        
        if role_seniority:
            if "senior" in role_seniority or "sr" in role_seniority:
                if years_exp >= 5:
                    seniority_score = 80
                elif years_exp >= 3:
                    seniority_score = 60
                else:
                    seniority_score = 30
            elif "junior" in role_seniority or "jr" in role_seniority:
                if years_exp <= 2:
                    seniority_score = 80
                elif years_exp <= 4:
                    seniority_score = 60
                else:
                    seniority_score = 40
        
        # Score promedio ponderado
        final_score = min(70, seniority_score + 20)  # Máximo 70 en fallback
        
        return ScoringResult(
            score=final_score,
            justification=f"Evaluación básica (IA no disponible: {error_message}). Score basado en años de experiencia ({years_exp}) y nivel de senioridad.",
            skill_match={
                "score": 50,
                "matched_skills": [],
                "missing_skills": [],
                "analysis": "No se pudo evaluar automáticamente (IA no disponible)"
            },
            experience_match={
                "score": min(100, years_exp * 10) if years_exp else 50,
                "years_candidate": years_exp,
                "years_required": "No especificado",
                "analysis": f"Candidato tiene {years_exp} años de experiencia"
            },
            seniority_match={
                "score": seniority_score,
                "candidate_level": "No determinado",
                "required_level": role.seniority or "No especificado",
                "analysis": "Evaluación básica por falla de IA"
            },
            industry_match={
                "score": 50,
                "candidate_industries": [],
                "target_industry": role_data.get("industry", "No especificada"),
                "analysis": "No se pudo evaluar automáticamente"
            },
            recommendations=[
                "Revisar manualmente el CV del candidato",
                "Verificar compatibilidad de skills técnicas específicas"
            ]
        )
    
    async def _log_scoring_event(
        self,
        application_id: str,
        score: float,
        justification: str,
        changed_by: str,
        db: AsyncSession
    ):
        """Registra el evento de scoring en el log de auditoría."""
        try:
            audit = HHAuditLog(
                entity_type="application",
                entity_id=application_id,
                action="update",
                changed_by=changed_by,
                diff_json={
                    "overall_score": {
                        "new": score,
                        "justification": justification[:500]  # Limitar longitud
                    }
                }
            )
            db.add(audit)
            await db.commit()
        except Exception as e:
            logger.error(f"Error al registrar auditoría de scoring: {e}")


# Instancia singleton del servicio
scoring_service = ScoringService()
