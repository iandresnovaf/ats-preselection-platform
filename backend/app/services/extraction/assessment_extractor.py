"""Extractor de datos de pruebas psicométricas."""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.services.extraction.models import AssessmentData, AssessmentDimension
from app.validators.data_cleaner import DataCleaner

logger = logging.getLogger(__name__)


class AssessmentExtractorError(Exception):
    """Error en extracción de assessments."""
    pass


class AssessmentExtractor:
    """Extrae datos estructurados de pruebas psicométricas."""
    
    # Nombres de pruebas conocidas
    KNOWN_TESTS = {
        'factor oscuro': 'Dark Factor Inventory',
        'dark factor': 'Dark Factor Inventory',
        'dfi': 'Dark Factor Inventory',
        'dark triad': 'Dark Triad',
        'triada oscura': 'Dark Triad',
        'inteligencia ejecutiva': 'Executive Intelligence',
        'executive intelligence': 'Executive Intelligence',
        'disc': 'DISC Assessment',
        'big five': 'Big Five Personality',
        'cinco grandes': 'Big Five Personality',
        '16pf': '16PF Personality',
        'mmi': 'Multimodal Interview',
        'hogan': 'Hogan Assessment',
        'papi': 'PAPI Personality',
    }
    
    # Dimensiones típicas de pruebas psicométricas
    KNOWN_DIMENSIONS = {
        # Dark Factor / Personalidad oscura
        'egocentrismo': 'Egocentrism',
        'egocentrism': 'Egocentrism',
        'egoísmo': 'Egoism',
        'egoism': 'Egoism',
        'moralidad': 'Moral Disengagement',
        'desapego moral': 'Moral Disengagement',
        'narcisismo': 'Narcissism',
        'narcissism': 'Narcissism',
        'sicopatía': 'Psychopathy',
        'psicopatía': 'Psychopathy',
        'psychopathy': 'Psychopathy',
        'manuabilidad': 'Manipulativeness',
        'manipulación': 'Manipulativeness',
        'manipulativeness': 'Manipulativeness',
        'machiavellian': 'Machiavellianism',
        'maquiavelismo': 'Machiavellianism',
        'mentalidad psicopática': 'Psychopathic Mindset',
        'volatilidad': 'Volatility',
        'volatility': 'Volatility',
        'sadismo': 'Sadism',
        'sadism': 'Sadism',
        'resentimiento': 'Spitefulness',
        'spitefulness': 'Spitefulness',
        'interés propio': 'Self-Interest',
        'self-interest': 'Self-Interest',
        'superioridad': 'Superiority',
        'superiority': 'Superiority',
        'indiferencia': 'Indifference',
        'indifference': 'Indifference',
        'crueldad': 'Cruelty',
        'cruelty': 'Cruelty',
        
        # DISC
        'dominancia': 'Dominance',
        'dominance': 'Dominance',
        'influencia': 'Influence',
        'influence': 'Influence',
        'estabilidad': 'Steadiness',
        'steadiness': 'Steadiness',
        'cumplimiento': 'Compliance',
        'compliance': 'Compliance',
        'conformidad': 'Compliance',
        
        # Big Five
        'apertura': 'Openness',
        'openness': 'Openness',
        'consciencia': 'Conscientiousness',
        'conscientiousness': 'Conscientiousness',
        'extraversión': 'Extraversion',
        'extraversion': 'Extraversion',
        'amabilidad': 'Agreeableness',
        'agreeableness': 'Agreeableness',
        'neuroticismo': 'Neuroticism',
        'neuroticism': 'Neuroticism',
        'estabilidad emocional': 'Emotional Stability',
        
        # Inteligencia Ejecutiva
        'integración': 'Integration',
        'imaginación': 'Imagination',
        'innovación': 'Innovation',
        'implementación': 'Implementation',
        'ejecución': 'Execution',
        'análisis': 'Analysis',
        'planeación': 'Planning',
        'planificación': 'Planning',
        'síntesis': 'Synthesis',
    }
    
    def __init__(self):
        self.cleaner = DataCleaner()
    
    async def extract_from_text(self, text: str, test_name_hint: Optional[str] = None) -> AssessmentData:
        """Extrae datos de assessment desde texto.
        
        Args:
            text: Texto extraído del documento
            test_name_hint: Nombre de la prueba (si se conoce)
            
        Returns:
            AssessmentData con los datos estructurados
        """
        if not text:
            raise AssessmentExtractorError("Texto vacío")
        
        text_clean = self.cleaner.clean_text(text)
        
        # Detectar nombre de la prueba
        detected_test_name = test_name_hint or self._detect_test_name(text_clean)
        
        # Extraer scores de dimensiones
        scores = self._extract_dimension_scores(text_clean)
        
        # Detectar sincerity/consistency score
        sincerity = self._extract_sincerity_score(text_clean)
        
        # Extraer nombre del candidato si está disponible
        candidate_name = self._extract_candidate_name(text_clean)
        
        # Extraer fecha de la prueba
        test_date = self._extract_test_date(text_clean)
        
        logger.info(
            f"Assessment extraído: {detected_test_name}, "
            f"{len(scores)} dimensiones, "
            f"sinceridad={sincerity}"
        )
        
        return AssessmentData(
            test_name=detected_test_name,
            test_type=self._classify_test_type(detected_test_name),
            candidate_name=candidate_name,
            test_date=test_date,
            scores=scores,
            sincerity_score=sincerity,
            raw_text=text[:5000]  # Guardar primeros 5000 chars
        )
    
    def _detect_test_name(self, text: str) -> str:
        """Detecta el nombre de la prueba.
        
        Args:
            text: Texto del documento
            
        Returns:
            Nombre de la prueba
        """
        text_lower = text.lower()
        
        # Buscar nombres conocidos
        for pattern, name in self.KNOWN_TESTS.items():
            if pattern in text_lower:
                return name
        
        # Buscar patrón genérico de título
        title_patterns = [
            r'(?:Resultado|Resultados|Reporte|Informe|Informe de)\s+de?\s*[:\-]?\s*([^\n]{3,50})',
            r'(?:Assessment|Evaluación|Prueba|Test)\s+(?:de|sobre)?\s*[:\-]?\s*([^\n]{3,50})',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self.cleaner.clean_text(match.group(1))
        
        return "Unknown Assessment"
    
    def _classify_test_type(self, test_name: str) -> Optional[str]:
        """Clasifica el tipo de prueba.
        
        Args:
            test_name: Nombre de la prueba
            
        Returns:
            Tipo de prueba
        """
        test_lower = test_name.lower()
        
        if any(x in test_lower for x in ['dark', 'oscuro', 'moral', 'narcis', 'sicopat', 'psicopat']):
            return 'personality_dark'
        elif any(x in test_lower for x in ['disc', 'comportamiento', 'behavioral']):
            return 'behavioral'
        elif any(x in test_lower for x in ['big five', 'cinco grandes', 'ocean']):
            return 'personality_big5'
        elif any(x in test_lower for x in ['inteligencia', 'intelligence', 'cognitiv']):
            return 'cognitive'
        elif any(x in test_lower for x in ['competencia', 'competency', 'skill']):
            return 'competency'
        else:
            return 'personality'
    
    def _extract_dimension_scores(self, text: str) -> List[AssessmentDimension]:
        """Extrae scores de dimensiones del texto.
        
        Args:
            text: Texto del documento
            
        Returns:
            Lista de dimensiones con scores
        """
        scores = []
        lines = text.split('\n')
        
        # Patrones para detectar filas de scores
        score_patterns = [
            # Patrón: Nombre ... Valor
            r'^\s*([^\d\n]{2,40})[\.\s]*(?:\d{1,3}[\.,]?\d*)\s*(?:/\s*100)?\s*$',
            # Patrón: Nombre: Valor
            r'^\s*([^:\n]{2,40})[:\-]\s*(\d{1,3}[\.,]?\d*)\s*(?:/\s*100)?\s*$',
            # Patrón en tablas: Valor | Nombre
            r'(?:^|\|)\s*(\d{1,3}[\.,]?\d*)\s*(?:/\s*100)?\s*(?:\||$)\s*([^\|\n]{2,40})',
            # Patrón con porcentaje
            r'^\s*([^\d\n]{2,40})[\.\s]*(\d{1,3})\s*%\s*$',
        ]
        
        # Procesar línea por línea
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            for pattern in score_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # Determinar cuál grupo es el nombre y cuál el valor
                    groups = [g for g in match.groups() if g]
                    if len(groups) >= 2:
                        # Intentar identificar cuál es el número
                        name = None
                        value = None
                        
                        for g in groups:
                            g = g.strip()
                            # Intentar parsear como número
                            try:
                                # Manejar comas y puntos decimales
                                num_str = g.replace(',', '.')
                                num = float(num_str)
                                if 0 <= num <= 100:
                                    value = num
                            except ValueError:
                                # Es texto, posiblemente el nombre
                                if len(g) > 2 and not name:
                                    name = g
                        
                        if name and value is not None:
                            dimension = self._create_dimension(name, value)
                            if dimension:
                                scores.append(dimension)
                    break
        
        # Si no se encontraron scores con patrones, intentar buscar en formato tabla
        if not scores:
            scores = self._extract_table_scores(text)
        
        # Remover duplicados manteniendo el primero
        seen = set()
        unique_scores = []
        for score in scores:
            key = score.name.lower()
            if key not in seen:
                seen.add(key)
                unique_scores.append(score)
        
        return unique_scores
    
    def _extract_table_scores(self, text: str) -> List[AssessmentDimension]:
        """Extrae scores de tablas.
        
        Args:
            text: Texto del documento
            
        Returns:
            Lista de dimensiones
        """
        scores = []
        
        # Buscar patrones de tabla: filas con múltiples columnas
        table_pattern = r'([^\|]*)\|\s*(\d{1,3}[\.,]?\d*)\s*(?:/\s*100)?'
        matches = re.findall(table_pattern, text)
        
        for name, value_str in matches:
            name = name.strip()
            try:
                value = float(value_str.replace(',', '.'))
                if 0 <= value <= 100 and len(name) > 2:
                    dimension = self._create_dimension(name, value)
                    if dimension:
                        scores.append(dimension)
            except ValueError:
                continue
        
        return scores
    
    def _create_dimension(self, name: str, value: float) -> Optional[AssessmentDimension]:
        """Crea una dimensión estandarizada.
        
        Args:
            name: Nombre de la dimensión
            value: Valor del score
            
        Returns:
            AssessmentDimension o None
        """
        name_clean = self.cleaner.clean_text(name)
        name_lower = name_clean.lower()
        
        # Buscar nombre estandarizado
        standard_name = self.KNOWN_DIMENSIONS.get(name_lower, name_clean)
        
        # Determinar categoría
        category = self._categorize_dimension(standard_name)
        
        # Asegurar que el valor esté en rango 0-100
        value = max(0, min(100, value))
        
        return AssessmentDimension(
            name=standard_name,
            value=round(value, 2),
            description=name_clean,
            category=category
        )
    
    def _categorize_dimension(self, dimension_name: str) -> Optional[str]:
        """Categoriza una dimensión.
        
        Args:
            dimension_name: Nombre de la dimensión
            
        Returns:
            Categoría
        """
        name_lower = dimension_name.lower()
        
        # Dark Factor categories
        dark_traits = [
            'egocentrism', 'egoism', 'narcissism', 'psychopathy',
            'manipulativeness', 'machiavellian', 'volatility', 'sadism',
            'spitefulness', 'self-interest', 'superiority', 'indifference',
            'cruelty', 'moral'
        ]
        
        if any(trait in name_lower for trait in dark_traits):
            return 'dark_factor'
        
        # DISC categories
        if dimension_name in ['Dominance', 'Influence', 'Steadiness', 'Compliance']:
            return 'disc'
        
        # Big Five categories
        big5 = ['Openness', 'Conscientiousness', 'Extraversion', 'Agreeableness', 'Neuroticism']
        if dimension_name in big5:
            return 'big5'
        
        # Cognitive
        cognitive = ['Integration', 'Imagination', 'Innovation', 'Implementation', 'Execution', 'Analysis', 'Planning', 'Synthesis']
        if dimension_name in cognitive:
            return 'cognitive'
        
        return 'other'
    
    def _extract_sincerity_score(self, text: str) -> Optional[float]:
        """Extrae el score de sinceridad/consistencia.
        
        Args:
            text: Texto del documento
            
        Returns:
            Score de sinceridad o None
        """
        patterns = [
            r'(?:sinceridad|sincerity|consistencia|consistency|validación|validation)\s*[:\-]?\s*(\d{1,3}[\.,]?\d*)',
            r'(?:escala\s+de\s+)?sinceridad\s*(?:\([^)]*\))?\s*[:\-]?\s*(\d{1,3}[\.,]?\d*)',
            r'(?:indicador\s+de\s+)?validez\s*[:\-]?\s*(\d{1,3}[\.,]?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(',', '.'))
                    return max(0, min(100, value))
                except ValueError:
                    continue
        
        return None
    
    def _extract_candidate_name(self, text: str) -> Optional[str]:
        """Extrae el nombre del candidato.
        
        Args:
            text: Texto del documento
            
        Returns:
            Nombre del candidato o None
        """
        patterns = [
            r'(?:candidato|candidata|candidate|persona evaluada|evaluado)[:\s]+([^\n]{2,50})',
            r'(?:nombre(?:\s+completo)?)[:\s]+([^\n]{2,50})',
            r'(?:apellido,?\s+nombre|nombre,?\s+apellido)[:\s]+([^\n]{2,50})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = self.cleaner.clean_name(match.group(1))
                if name and len(name) > 3:
                    return name
        
        return None
    
    def _extract_test_date(self, text: str) -> Optional[datetime]:
        """Extrae la fecha de la prueba.
        
        Args:
            text: Texto del documento
            
        Returns:
            Fecha o None
        """
        patterns = [
            r'(?:fecha\s+(?:de\s+)?(?:aplicación|prueba|test|evaluación|assessment))[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:fecha)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s*(?:fecha|date)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Intentar parsear fecha
                    for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except Exception:
                    continue
        
        return None
    
    def get_interpretation(self, scores: List[AssessmentDimension]) -> str:
        """Genera una interpretación básica de los scores.
        
        Args:
            scores: Lista de dimensiones con scores
            
        Returns:
            Interpretación en texto
        """
        if not scores:
            return "No hay scores disponibles para interpretar."
        
        high_scores = [s for s in scores if s.value >= 70]
        low_scores = [s for s in scores if s.value <= 30]
        
        parts = []
        
        if high_scores:
            parts.append(f"Puntuaciones altas en: {', '.join(s.name for s in high_scores)}.")
        
        if low_scores:
            parts.append(f"Puntuaciones bajas en: {', '.join(s.name for s in low_scores)}.")
        
        if not parts:
            parts.append("Puntuaciones dentro de rangos medios en todas las dimensiones.")
        
        return " ".join(parts)
