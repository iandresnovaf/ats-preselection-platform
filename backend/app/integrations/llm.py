"""Integración con LLM (OpenAI/Anthropic) para evaluación de candidatos."""
import logging
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.security import decrypt_value
from app.schemas import LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Resultado de la evaluación de un candidato."""
    score: float  # 0-100
    decision: str  # approved, rejected, pending
    strengths: List[str]
    gaps: List[str]
    red_flags: List[str]
    evidence: str
    raw_response: Optional[str] = None


class LLMClient:
    """Cliente para interactuar con proveedores de LLM."""
    
    PROVIDER_OPENAI = "openai"
    PROVIDER_ANTHROPIC = "anthropic"
    
    DECISION_APPROVED = "approved"
    DECISION_REJECTED = "rejected"
    DECISION_PENDING = "pending"
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Inicializa el cliente LLM.
        
        Args:
            config: Configuración del LLM. Si es None, se carga desde BD.
        """
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._initialized = False
        
    async def initialize(self, db_session=None):
        """Inicializa el cliente cargando configuración si es necesario."""
        # Importación lazy para evitar circular imports
        from app.services.configuration_service import ConfigurationService
        
        if self._initialized:
            return
            
        if self.config is None and db_session:
            service = ConfigurationService(db_session)
            self.config = await service.get_llm_config()
            
        if self.config is None:
            # Fallback a variables de entorno
            if settings.OPENAI_API_KEY:
                self.config = LLMConfig(
                    provider=self.PROVIDER_OPENAI,
                    api_key=settings.OPENAI_API_KEY,
                    model="gpt-4o-mini",
                    temperature=0.0
                )
            else:
                raise ValueError("No LLM configuration found")
        
        self._client = httpx.AsyncClient(timeout=60.0)
        self._initialized = True
        logger.info(f"LLM client initialized with provider: {self.config.provider}")
    
    async def close(self):
        """Cierra el cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Obtiene los headers para la API del proveedor."""
        if self.config.provider == self.PROVIDER_ANTHROPIC:
            return {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Anthropic-Version": "2023-06-01"
            }
        else:  # OpenAI
            return {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
    
    def _build_evaluate_prompt(self, candidate_data: Dict[str, Any], job_data: Dict[str, Any]) -> str:
        """Construye el prompt para evaluación de candidato.
        
        Args:
            candidate_data: Datos del candidato (CV parseado)
            job_data: Datos del job opening
            
        Returns:
            Prompt formateado
        """
        return f"""You are an expert technical recruiter evaluating candidates for a job position.

## JOB OPENING
Title: {job_data.get('title', 'N/A')}
Department: {job_data.get('department', 'N/A')}
Location: {job_data.get('location', 'N/A')}
Seniority: {job_data.get('seniority', 'N/A')}

Job Description:
{job_data.get('description', 'No description provided')}

## CANDIDATE CV
Name: {candidate_data.get('full_name', 'N/A')}
Email: {candidate_data.get('email', 'N/A')}

Raw CV Data:
```json
{json.dumps(candidate_data.get('raw_data', {}), indent=2, default=str)}
```

Extracted Skills: {json.dumps(candidate_data.get('extracted_skills', []))}
Extracted Experience: {json.dumps(candidate_data.get('extracted_experience', []), default=str)}
Extracted Education: {json.dumps(candidate_data.get('extracted_education', []), default=str)}

## EVALUATION INSTRUCTIONS
Analyze the candidate against the job requirements and provide a structured evaluation:

1. Calculate a match score (0-100) based on skills, experience, and education alignment
2. Make a decision: "approved" (strong match, proceed), "rejected" (poor fit), or "pending" (needs manual review)
3. List key strengths that match the job requirements
4. Identify any gaps or missing qualifications
5. Flag any concerns or red flags
6. Provide specific evidence from the CV that supports your evaluation

## OUTPUT FORMAT
Respond ONLY with a valid JSON object in this exact format:
```json
{{
  "score": <number 0-100>,
  "decision": "<approved|rejected|pending>",
  "strengths": ["<strength 1>", "<strength 2>", ...],
  "gaps": ["<gap 1>", "<gap 2>", ...],
  "red_flags": ["<flag 1>", "<flag 2>", ...],
  "evidence": "<specific evidence and reasoning>"
}}
```

Ensure your response is valid JSON. Do not include any text outside the JSON block."""

    def _build_questions_prompt(self, job_data: Dict[str, Any]) -> str:
        """Construye el prompt para generar preguntas de entrevista."""
        return f"""You are an expert technical interviewer preparing questions for a job interview.

## JOB OPENING
Title: {job_data.get('title', 'N/A')}
Department: {job_data.get('department', 'N/A')}
Seniority: {job_data.get('seniority', 'N/A')}

Job Description:
{job_data.get('description', 'No description provided')}

## TASK
Generate 5-8 interview questions that will help assess a candidate's fit for this position.
Include:
- Technical questions relevant to the role
- Behavioral questions
- Questions about past experience
- Questions to assess culture fit

## OUTPUT FORMAT
Respond ONLY with a valid JSON array of questions:
```json
[
  {{
    "question": "<question text>",
    "type": "<technical|behavioral|experience|cultural>",
    "purpose": "<what this question assesses>"
  }},
  ...
]
```"""

    def _build_summarize_prompt(self, cv_text: str) -> str:
        """Construye el prompt para resumir un CV."""
        return f"""You are an expert at analyzing and summarizing CVs/resumes.

## CV CONTENT
{cv_text}

## TASK
Provide a structured summary of this CV including:
- Key qualifications and expertise
- Years of experience
- Notable achievements
- Skills highlighted
- Education background
- Overall impression

## OUTPUT FORMAT
Respond ONLY with a valid JSON object:
```json
{{
  "summary": "<2-3 paragraph summary>",
  "key_skills": ["<skill 1>", "<skill 2>", ...],
  "years_experience": "<estimated years>",
  "education_level": "<highest education>",
  "notable_achievements": ["<achievement 1>", ...],
  "recommendations": "<suggested roles this candidate fits>"
}}
```"""

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _call_openai(self, prompt: str) -> str:
        """Llama a la API de OpenAI."""
        if not self._client:
            raise RuntimeError("Client not initialized")
            
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.config.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that responds only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config.temperature or 0.0,
            "max_tokens": self.config.max_tokens or 2000
        }
        
        response = await self._client.post(
            url,
            headers=self._get_headers(),
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _call_anthropic(self, prompt: str) -> str:
        """Llama a la API de Anthropic."""
        if not self._client:
            raise RuntimeError("Client not initialized")
            
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": self.config.model or "claude-3-haiku-20240307",
            "max_tokens": self.config.max_tokens or 2000,
            "temperature": self.config.temperature or 0.0,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = await self._client.post(
            url,
            headers=self._get_headers(),
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        return data["content"][0]["text"]
    
    async def _call_llm(self, prompt: str) -> str:
        """Llama al LLM según el proveedor configurado."""
        if not self._initialized:
            await self.initialize()
            
        if self.config.provider == self.PROVIDER_ANTHROPIC:
            return await self._call_anthropic(prompt)
        else:
            return await self._call_openai(prompt)
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extrae JSON de la respuesta del LLM."""
        # Intentar extraer JSON de bloques de código
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response}")
            raise ValueError(f"Invalid JSON response: {e}")
    
    async def evaluate_candidate(
        self, 
        candidate_data: Dict[str, Any], 
        job_data: Dict[str, Any]
    ) -> EvaluationResult:
        """Evalúa un candidato contra un job opening.
        
        Args:
            candidate_data: Datos del candidato
            job_data: Datos del job opening
            
        Returns:
            EvaluationResult con el score y análisis
        """
        logger.info(f"Evaluating candidate {candidate_data.get('full_name', 'Unknown')} "
                   f"for job {job_data.get('title', 'Unknown')}")
        
        try:
            prompt = self._build_evaluate_prompt(candidate_data, job_data)
            response = await self._call_llm(prompt)
            
            result_data = self._extract_json_from_response(response)
            
            # Validar y normalizar el resultado
            score = float(result_data.get("score", 0))
            score = max(0, min(100, score))  # Clamp entre 0-100
            
            decision = result_data.get("decision", self.DECISION_PENDING).lower()
            if decision not in [self.DECISION_APPROVED, self.DECISION_REJECTED, self.DECISION_PENDING]:
                decision = self.DECISION_PENDING
            
            return EvaluationResult(
                score=score,
                decision=decision,
                strengths=result_data.get("strengths", []),
                gaps=result_data.get("gaps", []),
                red_flags=result_data.get("red_flags", []),
                evidence=result_data.get("evidence", ""),
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Error evaluating candidate: {e}")
            # Fallback: retornar resultado pending
            return EvaluationResult(
                score=50,
                decision=self.DECISION_PENDING,
                strengths=[],
                gaps=["Error en evaluación automática"],
                red_flags=[],
                evidence=f"Error during evaluation: {str(e)}. Manual review required.",
                raw_response=None
            )
    
    async def generate_questions(self, job_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Genera preguntas de entrevista para un job opening.
        
        Args:
            job_data: Datos del job opening
            
        Returns:
            Lista de preguntas con tipo y propósito
        """
        logger.info(f"Generating interview questions for job: {job_data.get('title', 'Unknown')}")
        
        try:
            prompt = self._build_questions_prompt(job_data)
            response = await self._call_llm(prompt)
            
            questions = self._extract_json_from_response(response)
            
            if not isinstance(questions, list):
                logger.warning("LLM returned non-list for questions, returning empty list")
                return []
                
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            # Fallback: retornar preguntas genéricas
            return [
                {
                    "question": "Could you tell me about your relevant experience?",
                    "type": "experience",
                    "purpose": "Assess general background"
                },
                {
                    "question": "What interests you about this position?",
                    "type": "cultural",
                    "purpose": "Assess motivation and fit"
                }
            ]
    
    async def summarize_cv(self, cv_text: str) -> Dict[str, Any]:
        """Resume un CV en texto plano.
        
        Args:
            cv_text: Texto del CV
            
        Returns:
            Diccionario con el resumen estructurado
        """
        logger.info("Summarizing CV text")
        
        try:
            # Truncar si es muy largo
            max_chars = 15000
            if len(cv_text) > max_chars:
                cv_text = cv_text[:max_chars] + "\n... [truncated]"
            
            prompt = self._build_summarize_prompt(cv_text)
            response = await self._call_llm(prompt)
            
            summary = self._extract_json_from_response(response)
            return summary
            
        except Exception as e:
            logger.error(f"Error summarizing CV: {e}")
            # Fallback
            return {
                "summary": "Error generating summary. Manual review required.",
                "key_skills": [],
                "years_experience": "Unknown",
                "education_level": "Unknown",
                "notable_achievements": [],
                "recommendations": "Manual review required due to processing error"
            }


# Singleton para uso global
_llm_client: Optional[LLMClient] = None


async def get_llm_client(db_session=None) -> LLMClient:
    """Obtiene instancia singleton del cliente LLM."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
        await _llm_client.initialize(db_session)
    return _llm_client
