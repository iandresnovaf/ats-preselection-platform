"""Extractor de datos de CVs/Resumes."""
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.extraction.models import CVData, WorkExperience, Education
from app.validators.data_cleaner import DataCleaner

logger = logging.getLogger(__name__)


class CVExtractorError(Exception):
    """Error en extracción de CVs."""
    pass


class CVExtractor:
    """Extrae datos estructurados de CVs y resumes."""
    
    # Secciones comunes en CVs
    SECTION_PATTERNS = {
        'experience': [
            r'\b(experiencia\s+laboral|experiencia\s+profesional|work\s+experience|professional\s+experience|employment\s+history)\b',
            r'\b(historial\s+laboral|trayectoria\s+profesional)\b',
        ],
        'education': [
            r'\b(educación|educational|formación|academic|académico|studies|estudios)\b',
            r'\b(títulos|degrees|certifications|certificaciones)\b',
        ],
        'skills': [
            r'\b(habilidades|skills|competencias|competencies|capabilities|capacidades)\b',
            r'\b(conocimientos|technical\s+skills|tecnologías|technologies)\b',
        ],
        'summary': [
            r'\b(resumen|summary|perfil|profile|objective|objetivo|about\s+me|acerca\s+de)\b',
            r'\b(professional\s+summary|resumen\s+profesional)\b',
        ],
        'languages': [
            r'\b(idiomas|languages|lenguajes)\b',
        ],
    }
    
    def __init__(self):
        self.cleaner = DataCleaner()
    
    async def extract_from_text(self, text: str) -> CVData:
        """Extrae datos de CV desde texto.
        
        Args:
            text: Texto extraído del CV
            
        Returns:
            CVData con los datos estructurados
        """
        if not text:
            raise CVExtractorError("Texto vacío")
        
        text_clean = self.cleaner.clean_text(text)
        
        # Extraer datos personales
        personal = self._extract_personal_info(text_clean)
        
        # Extraer experiencia laboral
        experience = self._extract_experience(text_clean)
        
        # Extraer educación
        education = self._extract_education(text_clean)
        
        # Extraer skills
        skills = self._extract_skills(text_clean)
        
        # Extraer idiomas
        languages = self._extract_languages(text_clean)
        
        # Extraer resumen
        summary = self._extract_summary(text_clean)
        
        # Extraer certificaciones
        certifications = self._extract_certifications(text_clean)
        
        logger.info(
            f"CV extraído: {personal.get('name', 'Unknown')}, "
            f"{len(experience)} experiencias, "
            f"{len(education)} educaciones, "
            f"{len(skills)} skills"
        )
        
        return CVData(
            full_name=personal.get('name'),
            email=personal.get('email'),
            phone=personal.get('phone'),
            location=personal.get('location'),
            linkedin=personal.get('linkedin'),
            summary=summary,
            experience=experience,
            education=education,
            skills=skills,
            languages=languages,
            certifications=certifications,
            raw_text=text[:3000]  # Guardar primeros 3000 chars
        )
    
    def _extract_personal_info(self, text: str) -> Dict[str, Any]:
        """Extrae información personal.
        
        Args:
            text: Texto del CV
            
        Returns:
            Diccionario con datos personales
        """
        info = {}
        
        # Buscar email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            info['email'] = self.cleaner.clean_email(email_match.group(0))
        
        # Buscar teléfono
        phone_patterns = [
            r'(?:tel[ée]fono|phone|celular|mobile|m[oó]vil)[:\s]+([\d\s\-\(\)\+]{8,20})',
            r'\b(\+?[\d\s\-\(\)]{8,20})\s*(?:tel[ée]fono|phone|celular)',
            r'\b(\+\d[\d\s\-\(\)]{7,18})\b',  # Formato internacional
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text, re.IGNORECASE)
            if phone_match:
                phone = self.cleaner.clean_phone(phone_match.group(1))
                if phone:
                    info['phone'] = phone
                    break
        
        # Buscar LinkedIn
        linkedin_pattern = r'(?:linkedin\.com/in/|linkedin[:\s]+)([\w\-]+)'
        linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_match:
            info['linkedin'] = f"https://linkedin.com/in/{linkedin_match.group(1)}"
        
        # Buscar ubicación (patrón simple)
        location_pattern = r'(?:ubicación|location|ciudad|city|dirección|address)[:\s]+([^\n,]{3,50})'
        location_match = re.search(location_pattern, text, re.IGNORECASE)
        if location_match:
            info['location'] = self.cleaner.clean_text(location_match.group(1))
        
        # Intentar extraer nombre (típicamente al inicio del documento)
        lines = text.split('\n')[:10]  # Primeras 10 líneas
        for line in lines:
            line = line.strip()
            # Buscar línea que parezca un nombre (2-4 palabras, sin números)
            if line and 2 <= len(line.split()) <= 4:
                if not re.search(r'\d|@|www|http', line):
                    # Verificar que no sea una sección
                    if not any(re.search(p, line, re.IGNORECASE) for patterns in self.SECTION_PATTERNS.values() for p in patterns):
                        info['name'] = self.cleaner.clean_name(line)
                        break
        
        return info
    
    def _extract_experience(self, text: str) -> List[WorkExperience]:
        """Extrae experiencia laboral.
        
        Args:
            text: Texto del CV
            
        Returns:
            Lista de experiencias laborales
        """
        experiences = []
        
        # Encontrar sección de experiencia
        exp_section = self._extract_section(text, 'experience')
        if not exp_section:
            return experiences
        
        # Dividir en entradas de experiencia
        # Patrones para detectar nuevas entradas
        entry_patterns = [
            r'(?:^|\n)\s*•\s*',  # Bullets
            r'(?:^|\n)\s*[-\*]\s*',  # Guiones
            r'(?:^|\n)\s*\d{4}',  # Año al inicio
        ]
        
        # Intentar dividir por líneas vacías o patrones
        entries = re.split(r'\n\s*\n', exp_section)
        
        for entry in entries:
            entry = entry.strip()
            if len(entry) < 20:
                continue
            
            exp = self._parse_experience_entry(entry)
            if exp and (exp.company or exp.title):
                experiences.append(exp)
        
        return experiences
    
    def _parse_experience_entry(self, entry_text: str) -> Optional[WorkExperience]:
        """Parsea una entrada de experiencia individual.
        
        Args:
            entry_text: Texto de la entrada
            
        Returns:
            WorkExperience o None
        """
        lines = entry_text.split('\n')
        if not lines:
            return None
        
        company = None
        title = None
        start_date = None
        end_date = None
        is_current = False
        description = []
        location = None
        
        # Buscar fechas en todo el texto
        date_patterns = [
            r'(\d{1,2}/\d{4}|\d{4})\s*[-–]\s*(\d{1,2}/\d{4}|\d{4}|present|actual|current)',
            r'(\d{4})\s*[-–]\s*(\d{4}|present|actual|current)',
            r'(\w+\s+\d{4})\s*[-–]\s*(\w+\s+\d{4}|present|actual|current)',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, entry_text, re.IGNORECASE)
            if match:
                start_date = match.group(1)
                end_raw = match.group(2).lower()
                if end_raw in ['present', 'actual', 'current', 'hoy']:
                    end_date = 'Present'
                    is_current = True
                else:
                    end_date = match.group(2)
                break
        
        # Primera línea usualmente tiene empresa y/o título
        first_line = lines[0].strip()
        
        # Buscar patrón: Título en Empresa
        at_pattern = r'(.+?)\s+(?:en|at|@)\s+(.+)'
        at_match = re.match(at_pattern, first_line, re.IGNORECASE)
        if at_match:
            title = self.cleaner.clean_job_title(at_match.group(1))
            company = self.cleaner.clean_company_name(at_match.group(2))
        else:
            # Intentar separar por comas o pipes
            parts = re.split(r'[,|]', first_line)
            if len(parts) >= 2:
                title = self.cleaner.clean_job_title(parts[0])
                company = self.cleaner.clean_company_name(parts[1])
            else:
                # Asumir que es el título
                title = self.cleaner.clean_job_title(first_line)
        
        # Resto del texto es descripción
        for line in lines[1:]:
            line = line.strip()
            if line and not re.match(r'^(20\d{2}|19\d{2}|present)', line, re.IGNORECASE):
                description.append(line)
        
        # Buscar ubicación en la descripción
        for line in description:
            loc_match = re.search(r'(?:ubicación|location|lugar|place)[:\s]+([^\n]+)', line, re.IGNORECASE)
            if loc_match:
                location = self.cleaner.clean_text(loc_match.group(1))
                break
        
        return WorkExperience(
            company=company,
            title=title,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
            description='\n'.join(description) if description else None,
            location=location
        )
    
    def _extract_education(self, text: str) -> List[Education]:
        """Extrae educación.
        
        Args:
            text: Texto del CV
            
        Returns:
            Lista de educación
        """
        educations = []
        
        # Encontrar sección de educación
        edu_section = self._extract_section(text, 'education')
        if not edu_section:
            return educations
        
        # Dividir en entradas
        entries = re.split(r'\n\s*\n', edu_section)
        
        for entry in entries:
            entry = entry.strip()
            if len(entry) < 15:
                continue
            
            edu = self._parse_education_entry(entry)
            if edu and (edu.institution or edu.degree):
                educations.append(edu)
        
        return educations
    
    def _parse_education_entry(self, entry_text: str) -> Optional[Education]:
        """Parsea una entrada de educación.
        
        Args:
            entry_text: Texto de la entrada
            
        Returns:
            Education o None
        """
        lines = entry_text.split('\n')
        if not lines:
            return None
        
        institution = None
        degree = None
        field_of_study = None
        start_date = None
        end_date = None
        is_current = False
        
        # Buscar fechas
        date_patterns = [
            r'(\d{4})\s*[-–]\s*(\d{4}|present|actual)',
            r'(\d{4})\s*[-–]?\s*(\d{4})?',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, entry_text, re.IGNORECASE)
            if match:
                start_date = match.group(1)
                end_raw = match.group(2)
                if end_raw and end_raw.lower() in ['present', 'actual', 'current']:
                    end_date = 'Present'
                    is_current = True
                elif end_raw:
                    end_date = end_raw
                break
        
        # Primera línea suele tener institución y grado
        first_line = lines[0].strip()
        
        # Buscar patrón: Grado en Institución
        at_pattern = r'(.+?)\s+(?:en|at|de)\s+(.+)'
        at_match = re.match(at_pattern, first_line, re.IGNORECASE)
        if at_match:
            degree = self.cleaner.standardize_degree(at_match.group(1))
            institution = self.cleaner.clean_company_name(at_match.group(2))
        else:
            parts = first_line.split(',')
            if len(parts) >= 2:
                degree = self.cleaner.standardize_degree(parts[0])
                institution = self.cleaner.clean_company_name(parts[1])
            else:
                institution = self.cleaner.clean_company_name(first_line)
        
        # Buscar campo de estudio en líneas siguientes
        for line in lines[1:]:
            field_match = re.search(r'(?:carrera|field|major|specialization|especialidad)[:\s]+([^\n]+)', line, re.IGNORECASE)
            if field_match:
                field_of_study = self.cleaner.clean_text(field_match.group(1))
                break
        
        return Education(
            institution=institution,
            degree=degree,
            field_of_study=field_of_study,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current
        )
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extrae skills.
        
        Args:
            text: Texto del CV
            
        Returns:
            Lista de skills
        """
        skills = []
        
        # Encontrar sección de skills
        skills_section = self._extract_section(text, 'skills')
        if skills_section:
            # Extraer skills de la sección
            skills = self._parse_skills_text(skills_section)
        
        # También buscar skills en todo el documento (lenguajes de programación, etc.)
        tech_skills = self._extract_technical_skills(text)
        
        # Combinar y deduplicar
        all_skills = skills + [s for s in tech_skills if s.lower() not in [x.lower() for x in skills]]
        
        return self.cleaner.clean_skills_list(all_skills)
    
    def _parse_skills_text(self, text: str) -> List[str]:
        """Parsea texto de skills.
        
        Args:
            text: Texto de skills
            
        Returns:
            Lista de skills
        """
        skills = []
        
        # Separar por comas, bullets o pipes
        parts = re.split(r'[,;|•\-\*\n]', text)
        
        for part in parts:
            skill = part.strip()
            if skill and len(skill) > 1 and len(skill) < 50:
                # Evitar cosas que claramente no son skills
                if not re.match(r'^(experiencia|education|habilidades|skills)', skill, re.IGNORECASE):
                    skills.append(skill)
        
        return skills
    
    def _extract_technical_skills(self, text: str) -> List[str]:
        """Extrae skills técnicas del texto completo.
        
        Args:
            text: Texto completo
            
        Returns:
            Lista de skills técnicas
        """
        # Lista de tecnologías comunes a buscar
        tech_patterns = [
            r'\b(Python|JavaScript|TypeScript|Java|C\+\+|C#|Go|Rust|Ruby|PHP|Swift|Kotlin)\b',
            r'\b(React|Angular|Vue|Node\.js|Express|Django|Flask|FastAPI|Spring)\b',
            r'\b(AWS|GCP|Azure|Docker|Kubernetes|Terraform|CI/CD|Jenkins|GitHub Actions)\b',
            r'\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|DynamoDB)\b',
            r'\b(Machine Learning|Deep Learning|AI|Data Science|TensorFlow|PyTorch)\b',
        ]
        
        found_skills = set()
        for pattern in tech_patterns:
            matches = re.findall(pattern, text)
            found_skills.update(matches)
        
        return list(found_skills)
    
    def _extract_languages(self, text: str) -> List[str]:
        """Extrae idiomas.
        
        Args:
            text: Texto del CV
            
        Returns:
            Lista de idiomas
        """
        languages = []
        
        # Encontrar sección de idiomas
        lang_section = self._extract_section(text, 'languages')
        if lang_section:
            # Buscar idiomas conocidos
            lang_pattern = r'\b(Español|Spanish|Inglés|English|Francés|French|Alemán|German|Portugués|Portuguese|Italiano|Italian|Chino|Chinese|Japonés|Japanese)\b'
            matches = re.findall(lang_pattern, lang_section, re.IGNORECASE)
            languages = list(set(matches))
        
        return languages
    
    def _extract_summary(self, text: str) -> Optional[str]:
        """Extrae resumen profesional.
        
        Args:
            text: Texto del CV
            
        Returns:
            Resumen o None
        """
        # Encontrar sección de resumen
        summary_section = self._extract_section(text, 'summary')
        if summary_section:
            return self.cleaner.clean_cv_summary(summary_section)
        
        return None
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extrae certificaciones.
        
        Args:
            text: Texto del CV
            
        Returns:
            Lista de certificaciones
        """
        certifications = []
        
        # Buscar sección de certificaciones
        cert_patterns = [
            r'(?:certificaciones|certifications)[:\s]*\n(.*?)(?=\n\s*\n|\Z)',
        ]
        
        for pattern in cert_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                cert_text = match.group(1)
                lines = cert_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 5:
                        certifications.append(self.cleaner.clean_text(line))
        
        return certifications
    
    def _extract_section(self, text: str, section_type: str) -> Optional[str]:
        """Extrae una sección específica del texto.
        
        Args:
            text: Texto completo
            section_type: Tipo de sección
            
        Returns:
            Contenido de la sección o None
        """
        patterns = self.SECTION_PATTERNS.get(section_type, [])
        
        for pattern in patterns:
            # Buscar el patrón de sección
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Encontrar el inicio de la sección
                start = match.end()
                
                # Encontrar el final (próxima sección o fin del documento)
                remaining = text[start:]
                
                # Buscar el inicio de la siguiente sección
                next_section_match = None
                for other_patterns in self.SECTION_PATTERNS.values():
                    for other_pattern in other_patterns:
                        m = re.search(other_pattern, remaining, re.IGNORECASE)
                        if m:
                            if next_section_match is None or m.start() < next_section_match.start():
                                next_section_match = m
                
                if next_section_match:
                    section_text = remaining[:next_section_match.start()]
                else:
                    section_text = remaining
                
                return section_text.strip()
        
        return None
