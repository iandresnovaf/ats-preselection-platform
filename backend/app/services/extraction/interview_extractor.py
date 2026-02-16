"""Extractor de datos de entrevistas."""
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from textblob import TextBlob

from app.services.extraction.models import InterviewData, InterviewQuote
from app.validators.data_cleaner import DataCleaner

logger = logging.getLogger(__name__)


class InterviewExtractorError(Exception):
    """Error en extracción de entrevistas."""
    pass


class InterviewExtractor:
    """Extrae datos estructurados de notas de entrevistas."""
    
    # Patrones para detectar preguntas comunes
    QUESTION_PATTERNS = [
        r'(?:cuéntame|tell\s+me|háblame|talk\s+to\s+me)\s+(?:sobre|about)',
        r'(?:por\s+qué|why)\s+(?:deberíamos|should)',
        r'(?:cuál|what)\s+(?:es|is)\s+(?:tu|your)\s+(?:fortaleza|strength|debilidad|weakness)',
        r'(?:dónde|where)\s+(?:te|do\s+you)\s+(?:ves|see\s+yourself)',
        r'(?:describe|describa)\s+(?:un|a)\s+(?:momento|time|situación|situation)',
    ]
    
    # Palabras clave para detectar riesgos
    RISK_KEYWORDS = {
        'high': [
            'despedido', 'fired', 'demandado', 'sued', 'hostil', 'hostile',
            'agresión', 'aggression', 'violencia', 'violence', 'drogas', 'drugs',
            'fraude', 'fraud', 'robo', 'theft', 'mentir', 'lying', 'falsificar',
        ],
        'medium': [
            'conflicto', 'conflict', 'discusión', 'argument', 'problema', 'problem',
            'dificultad', 'difficulty', 'desacuerdo', 'disagreement', 'tensión', 'tension',
            'queja', 'complaint', 'reclamo', 'grievance', 'sanción', 'sanction',
        ],
        'low': [
            'retraso', 'delay', 'tardanza', 'late', 'ausencia', 'absence',
            'mejora', 'improvement needed', 'desarrollo', 'development needed',
        ]
    }
    
    # Palabras clave para detectar fortalezas
    STRENGTH_KEYWORDS = [
        'liderazgo', 'leadership', 'iniciativa', 'initiative', 'proactivo', 'proactive',
        'resultados', 'results', 'logros', 'achievements', 'éxito', 'success',
        'excelente', 'excellent', 'destacado', 'outstanding', 'superior',
        'innovación', 'innovation', 'creatividad', 'creativity', 'solución', 'solution',
        'trabajo en equipo', 'teamwork', 'colaboración', 'collaboration',
        'comunicación', 'communication', 'negociación', 'negotiation',
        'adaptabilidad', 'adaptability', 'flexibilidad', 'flexibility',
    ]
    
    # Palabras clave para detectar preocupaciones
    CONCERN_KEYWORDS = [
        'falta', 'lack', 'carencia', 'deficiency', 'ausencia', 'absence',
        'limitado', 'limited', 'insuficiente', 'insufficient', 'débil', 'weak',
        'necesita', 'needs', 'requiere', 'requires', 'mejora', 'improvement',
        'inexperiencia', 'inexperience', 'novato', 'novice', 'principiante', 'beginner',
        'duda', 'doubt', 'incertidumbre', 'uncertainty', 'riesgo', 'risk',
    ]
    
    def __init__(self):
        self.cleaner = DataCleaner()
    
    async def extract_from_text(self, text: str, 
                               interview_type: Optional[str] = None,
                               interviewer: Optional[str] = None,
                               date: Optional[datetime] = None) -> InterviewData:
        """Extrae datos de entrevista desde texto.
        
        Args:
            text: Texto de la entrevista
            interview_type: Tipo de entrevista (opcional)
            interviewer: Nombre del entrevistador (opcional)
            date: Fecha de la entrevista (opcional)
            
        Returns:
            InterviewData con los datos estructurados
        """
        if not text:
            raise InterviewExtractorError("Texto vacío")
        
        text_clean = self.cleaner.clean_text(text)
        
        # Detectar tipo si no se proporciona
        if not interview_type:
            interview_type = self._detect_interview_type(text_clean)
        
        # Extraer citas clave
        quotes = self._extract_quotes(text_clean)
        
        # Detectar flags de riesgo
        flags = self._detect_risk_flags(text_clean)
        
        # Detectar fortalezas
        strengths = self._detect_strengths(text_clean)
        
        # Detectar preocupaciones
        concerns = self._detect_concerns(text_clean)
        
        # Calcular sentimiento general
        sentiment = self._analyze_sentiment(text_clean)
        
        # Generar resumen
        summary = self._generate_summary(text_clean, quotes, flags, strengths)
        
        # Determinar recomendación
        recommendation = self._determine_recommendation(flags, strengths, concerns, sentiment)
        
        logger.info(
            f"Entrevista extraída: tipo={interview_type}, "
            f"{len(quotes)} citas, "
            f"{len(flags)} flags, "
            f"sentimiento={sentiment}"
        )
        
        return InterviewData(
            interview_type=interview_type,
            interviewer=interviewer,
            date=date,
            summary=summary,
            key_quotes=quotes,
            flags=flags,
            strengths=strengths,
            concerns=concerns,
            overall_sentiment=sentiment,
            recommendation=recommendation,
            raw_text=text[:3000]
        )
    
    def _detect_interview_type(self, text: str) -> Optional[str]:
        """Detecta el tipo de entrevista.
        
        Args:
            text: Texto de la entrevista
            
        Returns:
            Tipo de entrevista
        """
        text_lower = text.lower()
        
        # Patrones para tipos de entrevista
        if any(re.search(p, text_lower) for p in ['técnica', 'technical', 'coding', 'código']):
            return 'technical'
        elif any(re.search(p, text_lower) for p in ['conductual', 'behavioral', 'situacional', 'situational']):
            return 'behavioral'
        elif any(re.search(p, text_lower) for p in ['cultural', 'cultura', 'fit']):
            return 'cultural_fit'
        elif any(re.search(p, text_lower) for p in ['competencias', 'competency', 'competencias']):
            return 'competency'
        elif any(re.search(p, text_lower) for p in ['final', 'fin', 'cierre', 'closing']):
            return 'final'
        elif any(re.search(p, text_lower) for p in ['inicial', 'initial', 'screening']):
            return 'screening'
        else:
            return 'general'
    
    def _extract_quotes(self, text: str) -> List[InterviewQuote]:
        """Extrae citas clave de la entrevista.
        
        Args:
            text: Texto de la entrevista
            
        Returns:
            Lista de citas
        """
        quotes = []
        
        # Buscar citas entre comillas
        quote_pattern = r'["""]([^"""]{20,300})["""]'
        matches = re.findall(quote_pattern, text)
        
        for match in matches:
            quote_text = match.strip()
            if quote_text:
                sentiment = self._analyze_sentiment(quote_text)
                category = self._categorize_quote(quote_text)
                
                quotes.append(InterviewQuote(
                    text=quote_text,
                    category=category,
                    sentiment=sentiment
                ))
        
        # Si no hay citas explícitas, extraer oraciones importantes
        if not quotes:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 50 and len(sentence) < 300:
                    # Buscar oraciones que mencionen riesgos o fortalezas
                    if any(kw in sentence.lower() for kw in self.RISK_KEYWORDS['high'] + self.STRENGTH_KEYWORDS):
                        sentiment = self._analyze_sentiment(sentence)
                        category = self._categorize_quote(sentence)
                        quotes.append(InterviewQuote(
                            text=sentence,
                            category=category,
                            sentiment=sentiment
                        ))
        
        # Limitar a las citas más relevantes (máximo 5)
        return quotes[:5]
    
    def _categorize_quote(self, quote: str) -> Optional[str]:
        """Categoriza una cita.
        
        Args:
            quote: Texto de la cita
            
        Returns:
            Categoría
        """
        quote_lower = quote.lower()
        
        # Detectar categoría
        if any(kw in quote_lower for kw in self.RISK_KEYWORDS['high'] + self.RISK_KEYWORDS['medium']):
            return 'risk'
        elif any(kw in quote_lower for kw in self.STRENGTH_KEYWORDS):
            return 'strength'
        elif any(kw in quote_lower for kw in self.CONCERN_KEYWORDS):
            return 'concern'
        elif any(re.search(p, quote_lower) for p in ['fortaleza', 'strength', 'strong']):
            return 'strength'
        elif any(re.search(p, quote_lower) for p in ['debilidad', 'weakness', 'weak']):
            return 'weakness'
        
        return 'general'
    
    def _detect_risk_flags(self, text: str) -> List[str]:
        """Detecta flags de riesgo.
        
        Args:
            text: Texto de la entrevista
            
        Returns:
            Lista de flags
        """
        flags = []
        text_lower = text.lower()
        
        # High risk
        for keyword in self.RISK_KEYWORDS['high']:
            if keyword in text_lower:
                # Encontrar contexto
                pattern = r'[^.]*\b' + re.escape(keyword) + r'\b[^.]{0,100}'
                match = re.search(pattern, text_lower)
                if match:
                    context = match.group(0).strip()
                    flags.append(f"HIGH RISK: {context[:100]}")
        
        # Medium risk
        for keyword in self.RISK_KEYWORDS['medium']:
            if keyword in text_lower:
                pattern = r'[^.]*\b' + re.escape(keyword) + r'\b[^.]{0,100}'
                match = re.search(pattern, text_lower)
                if match:
                    context = match.group(0).strip()
                    # Solo agregar si no es muy similar a uno ya agregado
                    if not any(context[:50] in f for f in flags):
                        flags.append(f"MEDIUM RISK: {context[:100]}")
        
        return flags[:5]  # Limitar a 5 flags
    
    def _detect_strengths(self, text: str) -> List[str]:
        """Detecta fortalezas mencionadas.
        
        Args:
            text: Texto de la entrevista
            
        Returns:
            Lista de fortalezas
        """
        strengths = []
        text_lower = text.lower()
        
        for keyword in self.STRENGTH_KEYWORDS:
            if keyword in text_lower:
                # Encontrar contexto
                pattern = r'[^.]*\b' + re.escape(keyword) + r'\b[^.]{0,100}'
                matches = re.findall(pattern, text_lower)
                for match in matches:
                    context = match.strip()
                    if len(context) > 20:
                        strengths.append(context[:150])
        
        # Deduplicar y limitar
        unique = []
        for s in strengths:
            if not any(s[:50] in u for u in unique):
                unique.append(s)
        
        return unique[:5]
    
    def _detect_concerns(self, text: str) -> List[str]:
        """Detecta preocupaciones.
        
        Args:
            text: Texto de la entrevista
            
        Returns:
            Lista de preocupaciones
        """
        concerns = []
        text_lower = text.lower()
        
        for keyword in self.CONCERN_KEYWORDS:
            if keyword in text_lower:
                pattern = r'[^.]*\b' + re.escape(keyword) + r'\b[^.]{0,100}'
                matches = re.findall(pattern, text_lower)
                for match in matches:
                    context = match.strip()
                    if len(context) > 20:
                        concerns.append(context[:150])
        
        # Deduplicar y limitar
        unique = []
        for c in concerns:
            if not any(c[:50] in u for u in unique):
                unique.append(c)
        
        return unique[:5]
    
    def _analyze_sentiment(self, text: str) -> str:
        """Analiza el sentimiento del texto.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Sentimiento: positive, negative, neutral, mixed
        """
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.3:
                return 'positive'
            elif polarity < -0.3:
                return 'negative'
            elif abs(polarity) < 0.1:
                return 'neutral'
            else:
                return 'mixed'
        except Exception as e:
            logger.warning(f"Error analizando sentimiento: {e}")
            return 'neutral'
    
    def _generate_summary(self, text: str, quotes: List[InterviewQuote], 
                         flags: List[str], strengths: List[str]) -> str:
        """Genera un resumen de la entrevista.
        
        Args:
            text: Texto completo
            quotes: Citas extraídas
            flags: Flags de riesgo
            strengths: Fortalezas
            
        Returns:
            Resumen
        """
        parts = []
        
        # Resumen básico
        parts.append(f"Entrevista procesada. "
                    f"{len(quotes)} citas clave identificadas. ")
        
        # Mencionar flags si existen
        if flags:
            high_risks = [f for f in flags if f.startswith('HIGH')]
            if high_risks:
                parts.append(f"Se detectaron {len(high_risks)} riesgos altos. ")
        
        # Mencionar fortalezas
        if strengths:
            parts.append(f"Se identificaron {len(strengths)} fortalezas. ")
        
        return ''.join(parts)
    
    def _determine_recommendation(self, flags: List[str], strengths: List[str],
                                  concerns: List[str], sentiment: str) -> str:
        """Determina la recomendación basada en el análisis.
        
        Args:
            flags: Flags de riesgo
            strengths: Fortalezas
            concerns: Preocupaciones
            sentiment: Sentimiento general
            
        Returns:
            Recomendación
        """
        high_risks = len([f for f in flags if f.startswith('HIGH')])
        medium_risks = len([f for f in flags if f.startswith('MEDIUM')])
        
        # Calcular score
        score = 0
        score += len(strengths) * 2
        score -= high_risks * 5
        score -= medium_risks * 2
        score -= len(concerns)
        
        # Ajustar por sentimiento
        if sentiment == 'positive':
            score += 3
        elif sentiment == 'negative':
            score -= 3
        
        # Determinar recomendación
        if high_risks > 0 or score < -5:
            return 'REJECT'
        elif score > 5 and sentiment in ['positive', 'neutral']:
            return 'PROCEED'
        else:
            return 'REVIEW'
