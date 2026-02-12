"""Servicio de parsing de CVs usando IA (OpenAI)."""
import json
import logging
import re
import time
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.models.rhtools import ResumeParse, Document, DocumentStatus

logger = logging.getLogger(__name__)


class ResumeParserError(Exception):
    """Error en parsing de CV."""
    pass


class ResumeParser:
    """Parser de CVs usando OpenAI GPT-4."""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else None
        self.model = "gpt-4o-mini"  # Modelo por defecto
        
    async def parse_resume(self, document_id: str, extracted_text: str) -> Dict[str, Any]:
        """
        Parsear un CV usando OpenAI.
        
        Args:
            document_id: ID del documento
            extracted_text: Texto extraído del CV
            
        Returns:
            Dict con los datos estructurados del CV
        """
        if not self.api_key:
            raise ResumeParserError("OpenAI API key not configured")
        
        prompt = self._build_prompt(extracted_text)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are a resume parser. Extract structured information from CVs."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=60.0
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Extraer el contenido JSON
                content = data["choices"][0]["message"]["content"]
                parsed_data = json.loads(content)
                
                # Calcular score de confianza
                confidence = self._calculate_confidence(parsed_data)
                
                return {
                    "parsed_data": parsed_data,
                    "confidence_score": confidence,
                    "model_used": self.model,
                    "tokens_used": data.get("usage", {}).get("total_tokens", 0)
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.text}")
            raise ResumeParserError(f"OpenAI API error: {e.response.status_code}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise ResumeParserError("Failed to parse OpenAI response")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise ResumeParserError(f"Unexpected error: {str(e)}")
    
    def _build_prompt(self, cv_text: str) -> str:
        """Construir el prompt para OpenAI."""
        return f"""Extract the following information from this resume/CV and return it as JSON:

Resume text:
{cv_text[:8000]}  # Limitar a 8000 chars para no exceder tokens

Extract and return this JSON structure:
{{
    "name": "Full name of the candidate",
    "email": "Email address",
    "phone": "Phone number",
    "location": "City, Country",
    "linkedin": "LinkedIn URL if present",
    "summary": "Professional summary or profile",
    "experience": [
        {{
            "company": "Company name",
            "title": "Job title",
            "start_date": "Start date (YYYY-MM or YYYY)",
            "end_date": "End date (YYYY-MM, YYYY, or 'Present')",
            "description": "Job description"
        }}
    ],
    "education": [
        {{
            "institution": "School/University name",
            "degree": "Degree obtained",
            "start_date": "Start date",
            "end_date": "End date"
        }}
    ],
    "skills": ["skill1", "skill2", "skill3"]
}}

Return ONLY the JSON object, no markdown formatting."""
    
    def _calculate_confidence(self, parsed_data: Dict[str, Any]) -> float:
        """Calcular score de confianza basado en campos presentes."""
        score = 0.0
        
        # Campos básicos (40%)
        if parsed_data.get("name"):
            score += 0.20
        if parsed_data.get("email"):
            score += 0.20
            
        # Experiencia (30%)
        experience = parsed_data.get("experience", [])
        if experience and len(experience) > 0:
            score += 0.30
            
        # Educación (20%)
        education = parsed_data.get("education", [])
        if education and len(education) > 0:
            score += 0.20
            
        # Skills (10%)
        skills = parsed_data.get("skills", [])
        if skills and len(skills) > 0:
            score += 0.10
            
        return round(score, 2)
    
    async def save_parse_result(
        self, 
        document_id: str, 
        parsed_data: Dict[str, Any], 
        confidence_score: float,
        model_used: str
    ) -> ResumeParse:
        """Guardar el resultado del parsing en la base de datos."""
        from app.core.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            resume_parse = ResumeParse(
                document_id=document_id,
                extracted_text=parsed_data.get("summary", ""),
                parsed_json=parsed_data,
                confidence_score=confidence_score,
                model_id=model_used,
                model_version="1.0"
            )
            session.add(resume_parse)
            await session.commit()
            await session.refresh(resume_parse)
            return resume_parse
