"""Limpiadores de datos para el pipeline de documentos."""
import re
import unicodedata
from typing import Optional, List, Any
import logging

logger = logging.getLogger(__name__)


class DataCleaner:
    """Limpia y normaliza datos extraídos de documentos."""
    
    # Palabras comunes a remover en títulos
    STOP_WORDS = {
        'el', 'la', 'los', 'las', 'de', 'del', 'al', 'y', 'o', 'en', 'con',
        'the', 'of', 'and', 'or', 'in', 'with', 'at', 'from', 'to', 'for'
    }
    
    # Sufijos comunes en nombres de empresas
    COMPANY_SUFFIXES = [
        r'\s*,?\s*S\.?A\.?\s*$',
        r'\s*,?\s*S\.?A\.?S\.?\s*$',
        r'\s*,?\s*S\.?A\.?B\.?\s*$',
        r'\s*,?\s*LTD\.?\s*$',
        r'\s*,?\s*LIMITED\s*$',
        r'\s*,?\s*LLC\s*$',
        r'\s*,?\s*INC\.?\s*$',
        r'\s*,?\s*CORP\.?\s*$',
        r'\s*,?\s*GMBH\s*$',
        r'\s*,?\s*B\.?V\.?\s*$',
        r'\s*,?\s*S\.?L\.?\s*$',
        r'\s*,?\s*S\.?L\.?L\.?\s*$',
    ]
    
    def __init__(self):
        self.company_suffix_pattern = re.compile(
            '|'.join(self.COMPANY_SUFFIXES), 
            re.IGNORECASE
        )
    
    def clean_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Limpia texto general.
        
        Args:
            text: Texto a limpiar
            max_length: Longitud máxima opcional
            
        Returns:
            Texto limpio
        """
        if not text:
            return ""
        
        # Convertir a string si no lo es
        text = str(text)
        
        # Normalizar unicode (NFC para caracteres combinados)
        text = unicodedata.normalize('NFC', text)
        
        # Reemplazar múltiples espacios por uno solo
        text = re.sub(r'\s+', ' ', text)
        
        # Remover espacios al inicio y final
        text = text.strip()
        
        # Truncar si es necesario
        if max_length and len(text) > max_length:
            text = text[:max_length].strip()
        
        return text
    
    def clean_name(self, name: str, title_case: bool = True) -> str:
        """Limpia y normaliza nombres de personas.
        
        Args:
            name: Nombre a limpiar
            title_case: Si aplicar Title Case
            
        Returns:
            Nombre limpio
        """
        if not name:
            return ""
        
        name = self.clean_text(name)
        
        # Remover títulos honoríficos comunes
        prefixes = [
            r'^\s*(?:Sr\.?|Sra\.?|Dr\.?|Dra\.?|Prof\.?|Ing\.?|Lic\.?|M\.?Sc\.?|Ph\.?D\.?)\s+',
            r'^\s*(?:Mr\.?|Mrs\.?|Ms\.?|Miss|Dr\.?|Prof\.?)\s+',
        ]
        for prefix in prefixes:
            name = re.sub(prefix, '', name, flags=re.IGNORECASE)
        
        # Remover caracteres no válidos en nombres
        name = re.sub(r'[^\w\s\-\'\.]', '', name)
        
        if title_case:
            # Title Case inteligente (maneja apellidos como "de la Cruz")
            parts = name.split()
            cleaned_parts = []
            
            for i, part in enumerate(parts):
                part_lower = part.lower()
                
                # Si es una preposición y no es la primera palabra
                if part_lower in {'de', 'del', 'la', 'los', 'las', 'y', 'e', 'o', 'u', 'von', 'van', 'der', 'den', 'di', 'da'} and i > 0:
                    cleaned_parts.append(part_lower)
                else:
                    cleaned_parts.append(part.capitalize())
            
            name = ' '.join(cleaned_parts)
        
        return name.strip()
    
    def clean_company_name(self, name: str) -> str:
        """Limpia nombres de empresas.
        
        Args:
            name: Nombre de la empresa
            
        Returns:
            Nombre limpio
        """
        if not name:
            return ""
        
        name = self.clean_text(name)
        
        # Remover sufijos legales
        name = self.company_suffix_pattern.sub('', name)
        
        # Limpiar espacios resultantes
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def clean_job_title(self, title: str) -> str:
        """Limpia títulos de trabajo.
        
        Args:
            title: Título del trabajo
            
        Returns:
            Título limpio
        """
        if not title:
            return ""
        
        title = self.clean_text(title)
        
        # Remover nivel seniority redundante (ya se maneja aparte)
        seniority_patterns = [
            r'^\s*(?:Junior|Jr\.?|Senior|Sr\.?|Lead|Principal|Staff)\s+',
        ]
        for pattern in seniority_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        return title.strip()
    
    def clean_skill(self, skill: str) -> str:
        """Limpia y normaliza un skill.
        
        Args:
            skill: Skill a limpiar
            
        Returns:
            Skill limpio
        """
        if not skill:
            return ""
        
        skill = self.clean_text(skill)
        
        # Normalizar nombres de tecnologías comunes
        tech_normalizations = {
            'js': 'JavaScript',
            'javascript': 'JavaScript',
            'ts': 'TypeScript',
            'typescript': 'TypeScript',
            'py': 'Python',
            'python': 'Python',
            'reactjs': 'React',
            r'react\.js': 'React',
            'node': 'Node.js',
            'nodejs': 'Node.js',
            r'node\.js': 'Node.js',
            'postgres': 'PostgreSQL',
            'postgresql': 'PostgreSQL',
            'mongo': 'MongoDB',
            'mongodb': 'MongoDB',
            'aws': 'AWS',
            'amazon web services': 'AWS',
            'gcp': 'GCP',
            'google cloud': 'GCP',
            'azure': 'Azure',
            'docker': 'Docker',
            'kubernetes': 'Kubernetes',
            'k8s': 'Kubernetes',
        }
        
        skill_lower = skill.lower()
        for pattern, normalized in tech_normalizations.items():
            if re.match(f'^{pattern}$', skill_lower, re.IGNORECASE):
                return normalized
        
        return skill
    
    def clean_skills_list(self, skills: List[str]) -> List[str]:
        """Limpia una lista de skills.
        
        Args:
            skills: Lista de skills
            
        Returns:
            Lista limpia sin duplicados
        """
        if not skills:
            return []
        
        cleaned = []
        seen = set()
        
        for skill in skills:
            cleaned_skill = self.clean_skill(skill)
            
            if cleaned_skill and cleaned_skill.lower() not in seen:
                cleaned.append(cleaned_skill)
                seen.add(cleaned_skill.lower())
        
        return cleaned
    
    def clean_phone(self, phone: str) -> Optional[str]:
        """Limpia un número de teléfono (solo dígitos y +).
        
        Args:
            phone: Teléfono a limpiar
            
        Returns:
            Teléfono limpio o None
        """
        if not phone:
            return None
        
        # Conservar solo dígitos y +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Asegurar que empiece con +
        if not cleaned.startswith('+') and len(cleaned) > 0:
            # Intentar inferir código de país (configurable)
            cleaned = '+' + cleaned
        
        return cleaned if len(cleaned) > 3 else None
    
    def clean_email(self, email: str) -> Optional[str]:
        """Limpia un email.
        
        Args:
            email: Email a limpiar
            
        Returns:
            Email limpio o None
        """
        if not email:
            return None
        
        email = self.clean_text(email).lower()
        
        # Remover espacios
        email = email.replace(' ', '')
        
        # Validar formato básico
        if '@' not in email or '.' not in email.split('@')[-1]:
            return None
        
        return email
    
    def clean_url(self, url: str) -> Optional[str]:
        """Limpia y valida una URL.
        
        Args:
            url: URL a limpiar
            
        Returns:
            URL limpia o None
        """
        if not url:
            return None
        
        url = self.clean_text(url)
        
        # Agregar https:// si no tiene protocolo
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Validar formato básico
        if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', url, re.IGNORECASE):
            return None
        
        return url
    
    def clean_date_string(self, date_str: str) -> str:
        """Normaliza un string de fecha.
        
        Args:
            date_str: String de fecha
            
        Returns:
            Fecha normalizada
        """
        if not date_str:
            return ""
        
        date_str = self.clean_text(date_str)
        
        # Normalizar casos especiales
        if date_str.lower() in ['present', 'actual', 'current', 'now']:
            return 'Present'
        
        return date_str
    
    def remove_extra_whitespace(self, text: str) -> str:
        """Remueve espacios en blanco extras.
        
        Args:
            text: Texto a limpiar
            
        Returns:
            Texto limpio
        """
        if not text:
            return ""
        
        # Reemplazar múltiples espacios, tabs y newlines
        text = re.sub(r'[\s\t\n\r]+', ' ', text)
        return text.strip()
    
    def remove_html_tags(self, text: str) -> str:
        """Remueve tags HTML.
        
        Args:
            text: Texto con posible HTML
            
        Returns:
            Texto sin HTML
        """
        if not text:
            return ""
        
        # Remover tags HTML
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decodificar entidades HTML comunes
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' ',
        }
        
        for entity, char in html_entities.items():
            text = text.replace(entity, char)
        
        return self.remove_extra_whitespace(text)
    
    def clean_cv_summary(self, summary: str, max_sentences: int = 5) -> str:
        """Limpia el resumen profesional de un CV.
        
        Args:
            summary: Texto del resumen
            max_sentences: Máximo número de oraciones
            
        Returns:
            Resumen limpio
        """
        if not summary:
            return ""
        
        # Remover HTML si existe
        summary = self.remove_html_tags(summary)
        
        # Dividir en oraciones
        sentences = re.split(r'(?<=[.!?])\s+', summary)
        
        # Limitar número de oraciones
        if len(sentences) > max_sentences:
            sentences = sentences[:max_sentences]
        
        return ' '.join(sentences)
    
    def standardize_degree(self, degree: str) -> str:
        """Estandariza nombres de títulos académicos.
        
        Args:
            degree: Título académico
            
        Returns:
            Título estandarizado
        """
        if not degree:
            return ""
        
        degree = self.clean_text(degree)
        degree_lower = degree.lower()
        
        # Mapeo de títulos comunes
        degree_mapping = {
            'bachiller': 'Bachelor',
            'licenciatura': "Bachelor's Degree",
            'licenciado': "Bachelor's Degree",
            'pregrado': "Bachelor's Degree",
            'master': "Master's Degree",
            'maestría': "Master's Degree",
            'maestria': "Master's Degree",
            'mba': 'MBA',
            'doctorado': 'PhD',
            'phd': 'PhD',
            'ph.d': 'PhD',
            'ingeniería': 'Engineering',
            'ingenieria': 'Engineering',
            'tecnología': 'Technology',
            'tecnologia': 'Technology',
            'tsu': 'Associate Degree',
            'técnico': 'Technical Degree',
            'tecnico': 'Technical Degree',
        }
        
        for key, value in degree_mapping.items():
            if key in degree_lower:
                return value
        
        return degree
