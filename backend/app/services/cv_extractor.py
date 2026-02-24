"""
CV Extractor Service - Extracción avanzada de CVs
Extrae información estructurada de currículums usando patrones avanzados
"""
import re
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """Experiencia laboral extraída"""
    company: str = ""
    position: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    current: bool = False
    description: str = ""
    achievements: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)


@dataclass
class Education:
    """Educación extraída"""
    institution: str = ""
    degree: str = ""
    field: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""


@dataclass
class Skill:
    """Habilidad extraída"""
    name: str = ""
    level: str = "intermediate"
    category: str = ""


@dataclass
class Certification:
    """Certificación extraída"""
    name: str = ""
    institution: str = ""
    date: str = ""


@dataclass
class Language:
    """Idioma extraído"""
    name: str = ""
    level: str = ""


@dataclass
class Reference:
    """Referencia personal"""
    name: str = ""
    position: str = ""
    company: str = ""
    phone: str = ""
    email: str = ""


@dataclass
class CVData:
    """Datos completos de un CV"""
    full_name: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""
    address: str = ""
    location: str = ""
    city: str = ""
    country: str = ""
    national_id: str = ""
    birth_date: str = ""
    summary: str = ""
    headline: str = ""
    years_experience: int = 0
    linkedin_url: str = ""
    github_url: str = ""
    website: str = ""
    experiences: List[Experience] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)
    skills: List[Skill] = field(default_factory=list)
    certifications: List[Certification] = field(default_factory=list)
    languages: List[Language] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
    extraction_method: str = ""
    confidence_score: float = 0.0
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CVExtractor:
    """Extractor avanzado de información de CVs"""
    
    def __init__(self):
        self.cv_data = CVData()
    
    def extract_with_ai(self, text: str, filename: str = "") -> CVData:
        """Extrae información completa del CV"""
        self.cv_data.raw_text = text
        self._extract_personal_info(text)
        self._extract_profile(text)
        self._extract_experiences_enhanced(text)
        self._extract_education_enhanced(text)
        self._extract_skills_enhanced(text)
        self._extract_certifications(text)
        self._extract_languages(text)
        self._extract_references(text)
        self._calculate_confidence()
        return self.cv_data
    
    def _extract_personal_info(self, text: str):
        """Extraer información personal"""
        lines = text.split('\n')
        text_lower = text.lower()
        
        # Nombre - buscar en las primeras líneas
        # Buscar el patrón típico de nombre: 3-4 palabras, letras solo, sin números
        for line in lines[:20]:
            line = line.strip()
            # Filtrar líneas que son direcciones (tienen #, números, Apto, etc.)
            if any(char in line for char in ['#', 'Apto', 'Cra', 'Carrera', 'Calle', 'Transversal', 'Av.', 'Avenida', 'TEL', 'CEL', 'EMAIL']):
                continue
            # Filtrar líneas con números o símbolos
            if any(char.isdigit() for char in line):
                continue
            if '@' in line:
                continue
                
            words = line.split()
            # Nombre típico: 3-5 palabras, todas letras
            if (len(words) >= 3 and len(words) <= 5 and 
                len(line) > 12 and len(line) < 50 and
                all(word.isalpha() for word in words)):
                # Verificar que parezca un nombre (no empresa conocida)
                company_keywords = ['SEGUROS', 'CONSULTOR', 'CORPORATION', 'LTDA', 'S.A.', 'GROUP', 'GRUPO', 'COMPANY', 'EMPRESA']
                if not any(keyword in line.upper() for keyword in company_keywords):
                    self.cv_data.full_name = line
                    break
        
        # Email
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if email_match:
            self.cv_data.email = email_match.group(0)
        
        # Teléfonos - buscar varios formatos
        phone_patterns = [
            r'(?:celular|móvil|mobile)[\s:]*([\d\s\-\(\)\+]{7,20})',
            r'(?:teléfono|tel|phone)[\s:]*([\d\s\-\(\)\+]{7,20})',
            r'\b(3\d{2}[\s\-]?\d{3}[\s\-]?\d{4})\b',  # Colombia mobile
            r'\b(\d{3}[\s\-]?\d{3}[\s\-]?\d{4})\b',  # Generic
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, text_lower)
            if match:
                phone = match.group(1).strip() if match.groups() else match.group(0).strip()
                phone = re.sub(r'\s+', ' ', phone)
                if phone.startswith('3'):
                    self.cv_data.mobile = phone
                else:
                    self.cv_data.phone = phone
                break
        
        # Dirección - buscar patrón completo con número, apto, ciudad
        address_patterns = [
            # Patrón 1: Dirección explícita con "Dirección:" y ciudad al final
            r'(?:dirección|direccion|address)[\s:]*([A-Za-zÁÉÍÓÚáéíóúÑñ0-9\s,.#\-]+?(?:Bogot[áa]|Medell[íi]n|Cali)[\s,]*Colombia?)',
            # Patrón 2: Transversal/Calle/Carrera con número, #, y Apto
            r'(Transversal\s+\d+\s*(?:Este|Oeste|Sur|Norte)?\s*#?\s*\d+[A-Z]?[-\s]*\d+.*?Apto\.?\s*\d+.*?Bogot[áa])',
            r'(Carrera\s+\d+\s*#?\s*\d+[-\s]*\d+.*?Apto\.?\s*\d+.*?Bogot[áa])',
            r'(Calle\s+\d+\s*#?\s*\d+[-\s]*\d+.*?Apto\.?\s*\d+.*?Bogot[áa])',
        ]
        for pattern in address_patterns:
            address_match = re.search(pattern, text, re.IGNORECASE)
            if address_match:
                self.cv_data.address = address_match.group(1).strip()
                break
        
        # Extraer ciudad de la dirección
        if self.cv_data.address:
            city_match = re.search(r'(Bogot[áa]|Medell[íi]n|Cali)', self.cv_data.address, re.IGNORECASE)
            if city_match:
                self.cv_data.city = city_match.group(1)
        
        # Ciudad/ubicación
        location_match = re.search(r'(?:ubicación|ciudad|city)[\s:]*([A-Za-zÁÉÍÓÚáéíóúÑñ\s,]+?)(?:\n|$)', text_lower)
        if location_match:
            self.cv_data.location = location_match.group(1).strip()
        elif self.cv_data.address:
            # Extraer ciudad de la dirección
            city_match = re.search(r'(Bogot[áa]|Medell[íi]n|Cali|Barranquilla|Cartagena)', self.cv_data.address, re.IGNORECASE)
            if city_match:
                self.cv_data.city = city_match.group(1)
        
        # LinkedIn
        linkedin_match = re.search(r'linkedin\.com/in/[\w\-]+', text, re.IGNORECASE)
        if linkedin_match:
            self.cv_data.linkedin_url = f"https://www.{linkedin_match.group(0)}"
    
    def _extract_profile(self, text: str):
        """Extraer perfil profesional"""
        text_lower = text.lower()
        
        # Buscar sección de perfil profesional
        profile_section = re.search(
            r'(?:perfil profesional|professional profile|perfil)[\s:]*\n?([\s\S]{50,2000}?)(?=\n\s*(?:experiencia|experiencia laboral|work experience|educación|formación)|$)',
            text_lower, re.IGNORECASE
        )
        
        if profile_section:
            profile_text = profile_section.group(1).strip()
            # Limpiar
            profile_text = re.sub(r'\n+', ' ', profile_text)
            profile_text = re.sub(r'\s+', ' ', profile_text)
            self.cv_data.summary = profile_text[:1000]
        
        # Buscar años de experiencia mencionados
        years_match = re.search(r'(\d+)\s*(?:años?|years?)\s+de\s+experiencia', text_lower)
        if years_match:
            self.cv_data.years_experience = int(years_match.group(1))
    
    def _extract_experiences_enhanced(self, text: str):
        """Extraer experiencias laborales de forma mejorada"""
        text_lower = text.lower()
        
        # Encontrar la sección de experiencia
        exp_section_match = re.search(
            r'(?:experiencia laboral|experiencia profesional|work experience|employment|experiencia)[\s:]*\n?([\s\S]{100,15000}?)(?=\n\s*(?:educación|educacion|education|formación|formacion|academic|certificaciones|referencias|habilidades|skills)|$)',
            text_lower, re.IGNORECASE
        )
        
        if not exp_section_match:
            return
        
        exp_text = text[text_lower.find(exp_section_match.group(0)):text_lower.find(exp_section_match.group(0)) + len(exp_section_match.group(1))]
        
        # Dividir por empresas (líneas en MAYÚSCULAS o con palabras clave de empresa)
        # Patrones de empresa: todo mayúsculas, o termina en S.A., LTDA, etc.
        company_pattern = r'(?:^|\n)\s*([A-Z][A-Z\s&.,]+(?:S\.?A\.?|LTDA|LIMITADA|GROUP|GRUPO|CORP|INC|LLC)?)\s*(?:\n|$)'
        
        # Buscar bloques de experiencia
        # Cada bloque típicamente tiene: EMPRESA, Cargo, Periodo, Responsabilidades
        lines = exp_text.split('\n')
        
        current_exp = None
        collecting_description = False
        description_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            line_upper = line.upper()
            line_lower = line.lower()
            
            # Detectar empresa - debe ser TODA mayúsculas y parecer nombre de empresa
            # O contener palabras clave específicas de empresa
            is_company = False
            
            # Caso 1: Todo mayúsculas que parece empresa (no descripción)
            if line.isupper() and len(line) > 5 and len(line) < 70:
                # Verificar que parezca empresa: tiene palabras cortas típicas de empresas
                # o termina en S.A., LTDA, etc.
                company_indicators = ['SEGUROS', 'S.A.', 'LTDA', 'CORP', 'GROUP', 'GRUPO', 'COMPAÑÍA', 'COLOMBIA', 'ASEGURADORA']
                # O es corto (nombre de empresa típico) y no tiene preposiciones largas
                has_company_words = any(indicator in line_upper for indicator in company_indicators)
                is_short_name = len(line.split()) <= 6 and not any(word in line_lower for word in ['responsable', 'funciones', 'gestión', 'administración'])
                
                if has_company_words or is_short_name:
                    is_company = True
            
            # Caso 2: Contiene palabras clave específicas de empresa (no solo estar en mayúsculas)
            if not is_company and any(keyword in line_upper for keyword in ['SEGUROS S.A.', 'S.A.S.', 'COMPAÑÍA', 'CORPORACIÓN', 'LTDA.', 'LIMITADA']):
                if len(line) < 70 and not line.startswith('•') and not line.startswith('-'):
                    is_company = True
            
            # Detectar cargo explícito
            position_match = re.match(r'(?:cargo|position)[\s:]*(.+)', line_lower)
            is_position = position_match is not None or (
                any(word in line_lower for word in ['gerente', 'director', 'jefe', 'coordinador', 'especialista', 'analista', 'consultor', 'head', 'manager'])
                and len(line) < 80 and not line.isupper()
            )
            
            # Detectar período
            period_match = re.match(r'(?:periodo|period)[\s:]*(.+)', line_lower)
            is_period = period_match is not None or re.search(r'(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|\d{4})\s*[-–]\s*(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|\d{4}|actual|presente)', line_lower)
            
            # Detectar inicio de lista de responsabilidades
            is_responsibility_start = any(line.strip().startswith(bullet) for bullet in ['•', '-', '*', '▪', '○', '►'])
            
            if is_company and not line_lower.startswith('cargo') and not line_lower.startswith('periodo'):
                # Guardar experiencia anterior si existe
                if current_exp and (current_exp.company or current_exp.position):
                    if description_lines:
                        current_exp.description = '\n'.join(description_lines)
                        current_exp.responsibilities = description_lines
                    self.cv_data.experiences.append(current_exp)
                
                # Iniciar nueva experiencia
                current_exp = Experience(company=line)
                description_lines = []
                collecting_description = False
                
            elif current_exp:
                if position_match:
                    current_exp.position = position_match.group(1).strip()
                elif is_position and not current_exp.position and not line_lower.startswith('periodo'):
                    current_exp.position = line
                
                if period_match:
                    period_text = period_match.group(1).strip()
                    self._parse_period(period_text, current_exp)
                elif is_period and not current_exp.start_date:
                    self._parse_period(line, current_exp)
                
                if is_responsibility_start or collecting_description:
                    collecting_description = True
                    # Continuar coleccionando hasta nueva empresa o sección
                    if is_company or line_lower.startswith('cargo:'):
                        collecting_description = False
                    else:
                        description_lines.append(line)
        
        # Guardar última experiencia
        if current_exp and (current_exp.company or current_exp.position):
            if description_lines:
                current_exp.description = '\n'.join(description_lines)
                current_exp.responsibilities = description_lines
            self.cv_data.experiences.append(current_exp)
    
    def _parse_period(self, period_text: str, exp: Experience):
        """Parsear texto de período a fechas en formato yyyy-MM"""
        # Patrones comunes
        # "Noviembre 2022 – Actualmente"
        # "Agosto 2017 – Noviembre 2022"
        # "2012 – 2014"
        
        month_map = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06',
            'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        
        # Buscar fechas
        date_pattern = r'(\d{1,2})?\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)?\s*(\d{4})?\s*[-–]\s*(\d{1,2})?\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)?\s*(\d{4}|actual|presente)?'
        
        match = re.search(date_pattern, period_text.lower())
        if match:
            # Procesar fecha de inicio
            start_day = match.group(1)
            start_month = match.group(2)
            start_year = match.group(3)
            
            # Procesar fecha de fin
            end_day = match.group(4)
            end_month = match.group(5)
            end_year = match.group(6)
            
            # Formatear fecha de inicio como yyyy-MM
            if start_year:
                if start_month and start_month in month_map:
                    exp.start_date = f"{start_year}-{month_map[start_month]}"
                else:
                    exp.start_date = start_year
            
            # Formatear fecha de fin como yyyy-MM
            if end_year:
                if end_year in ['actual', 'presente']:
                    exp.end_date = ""
                    exp.current = True
                elif end_month and end_month in month_map:
                    exp.end_date = f"{end_year}-{month_map[end_month]}"
                else:
                    exp.end_date = end_year
            
            # Detectar si es actual
            if not exp.current:
                exp.current = any(word in period_text.lower() for word in ['actual', 'presente', 'actualmente'])
    
    def _extract_education_enhanced(self, text: str):
        """Extraer educación con fechas formateadas"""
        text_lower = text.lower()
        
        edu_section = re.search(
            r'(?:educación|educacion|education|formación|formacion|estudios|academic)[\s:]*\n?([\s\S]{50,3000}?)(?=\n\s*(?:experiencia|habilidades|skills|certificaciones|referencias)|$)',
            text_lower, re.IGNORECASE
        )
        
        if not edu_section:
            return
        
        edu_text = edu_section.group(1)
        lines = edu_text.split('\n')
        
        current_edu = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            
            # Detectar institución
            is_institution = any(word in line_lower for word in ['universidad', 'instituto', 'colegio', 'escuela', 'academia', 'university', 'college', 'institute'])
            
            # Detectar título
            is_degree = any(word in line_lower for word in ['especialización', 'maestría', 'doctorado', 'pregrado', 'posgrado', 'bachiller', 'técnico', 'tecnólogo', 'administrador', 'ingeniero', 'licenciado'])
            
            # Detectar fechas de educación (ej: 1998–2004)
            date_match = re.search(r'(\d{4})\s*[-–]\s*(\d{4}|presente|actual)', line_lower)
            if date_match:
                if current_edu:
                    start_year = date_match.group(1)
                    end_year = date_match.group(2)
                    current_edu.start_date = f"{start_year}-01"  # Enero por defecto
                    if end_year in ['presente', 'actual']:
                        current_edu.end_date = ""
                    else:
                        current_edu.end_date = f"{end_year}-12"  # Diciembre por defecto
                continue
            
            # Detectar año suelto (ej: "1998" o "(2008)")
            single_year_match = re.search(r'\(?\s*(\d{4})\s*\)?', line)
            if single_year_match and len(line) < 20:  # Solo si la línea es corta (es solo el año)
                year = single_year_match.group(1)
                # Verificar que parezca un año de estudio (no un teléfono o código)
                if 1950 <= int(year) <= 2030:
                    if current_edu and not current_edu.start_date:
                        current_edu.start_date = f"{year}-01"
                    continue
            
            if is_institution or is_degree or line.startswith('•') or line.startswith('-'):
                if current_edu and (current_edu.institution or current_edu.degree):
                    self.cv_data.education.append(current_edu)
                
                current_edu = Education()
                if is_institution:
                    current_edu.institution = line
                elif is_degree:
                    current_edu.degree = line
            elif current_edu:
                if not current_edu.institution and len(line) > 5:
                    current_edu.institution = line
                elif not current_edu.degree and len(line) > 5:
                    current_edu.degree = line
        
        if current_edu and (current_edu.institution or current_edu.degree):
            self.cv_data.education.append(current_edu)
        
        # Post-procesamiento: asegurar formato correcto de fechas yyyy-MM
        for edu in self.cv_data.education:
            # Normalizar start_date
            if edu.start_date:
                start = edu.start_date.strip()
                # Si es solo 4 dígitos (año), agregar -01
                if re.match(r'^\d{4}$', start):
                    edu.start_date = f"{start}-01"
                # Si tiene formato yyyy-M, agregar el 0
                elif re.match(r'^\d{4}-\d{1}$', start):
                    edu.start_date = f"{start}0"
            
            # Normalizar end_date
            if edu.end_date:
                end = edu.end_date.strip()
                # Si es solo 4 dígitos (año), agregar -12
                if re.match(r'^\d{4}$', end):
                    edu.end_date = f"{end}-12"
                # Si tiene formato yyyy-M, agregar el 0
                elif re.match(r'^\d{4}-\d{1}$', end):
                    edu.end_date = f"{end}0"
            
            # Debug logging
            print(f"  📚 Edu: {edu.institution[:30] if edu.institution else 'N/A'}... | "
                  f"Dates: {edu.start_date} - {edu.end_date}")
    
    def _extract_skills_enhanced(self, text: str):
        """Extraer habilidades"""
        text_lower = text.lower()
        
        skills_section = re.search(
            r'(?:habilidades|skills|competencias|conocimientos)[\s:]*\n?([\s\S]{50,2000}?)(?=\n\s*(?:experiencia|educación|certificaciones|referencias)|$)',
            text_lower, re.IGNORECASE
        )
        
        if skills_section:
            skills_text = skills_section.group(1)
            # Separar por líneas o comas
            skills_list = re.split(r'[,\n•\-]', skills_text)
            for skill in skills_list:
                skill = skill.strip()
                if skill and len(skill) > 2 and len(skill) < 50:
                    self.cv_data.skills.append(Skill(name=skill))
    
    def _extract_certifications(self, text: str):
        """Extraer certificaciones"""
        text_lower = text.lower()
        
        cert_section = re.search(
            r'(?:certificaciones|certifications|certificados)[\s:]*\n?([\s\S]{50,1500}?)(?=\n\s*(?:idiomas|languages|referencias|intereses)|$)',
            text_lower, re.IGNORECASE
        )
        
        if cert_section:
            cert_text = cert_section.group(1)
            lines = cert_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 5 and len(line) < 100 and not line.isupper():
                    self.cv_data.certifications.append(Certification(name=line))
    
    def _extract_languages(self, text: str):
        """Extraer idiomas"""
        text_lower = text.lower()
        
        lang_section = re.search(
            r'(?:idiomas|languages)[\s:]*\n?([\s\S]{50,800}?)(?=\n\s*(?:referencias|intereses)|$)',
            text_lower, re.IGNORECASE
        )
        
        if lang_section:
            lang_text = lang_section.group(1)
            # Buscar patrones de idioma: "Inglés - Avanzado", "Español: Nativo"
            lang_pattern = r'\b(ingl[eé]s|espa[ñn]ol|franc[eé]s|portugu[eé]s|alem[áa]n|italiano|chino|japon[eé]s)\b[\s:–\-]*(nativo|flu[ií]do|avanzado|intermedio|b[aá]sico|native|fluent|advanced|intermediate|basic)?'
            
            matches = re.findall(lang_pattern, lang_text, re.IGNORECASE)
            for lang, level in matches:
                self.cv_data.languages.append(Language(
                    name=lang.capitalize(),
                    level=level.capitalize() if level else "Intermedio"
                ))
    
    def _extract_references(self, text: str):
        """Extraer referencias personales"""
        text_lower = text.lower()
        
        ref_section = re.search(
            r'(?:referencias personales|referencias|references)[\s:]*\n?([\s\S]{50,2000}?)(?=\n\s*(?:intereses|hobbies|$)|$)',
            text_lower, re.IGNORECASE
        )
        
        if ref_section:
            ref_text = ref_section.group(1)
            # Buscar patrones: Nombre - Cargo - Empresa - Tel
            lines = ref_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:
                    line_lower = line.lower()
                    # Intentar extraer nombre, cargo, teléfono
                    ref = Reference()
                    parts = line.split('-')
                    if len(parts) >= 2:
                        ref.name = parts[0].strip()
                        ref.position = parts[1].strip() if len(parts) > 1 else ""
                        # Buscar teléfono
                        phone_match = re.search(r'(?:cel|tel)[\s:]*(\d{7,15})', line_lower)
                        if phone_match:
                            ref.phone = phone_match.group(1)
                        self.cv_data.references.append(ref)
    
    def _calculate_confidence(self):
        """Calcular score de confianza"""
        score = 0
        fields = [
            (self.cv_data.full_name, 10),
            (self.cv_data.email, 10),
            (self.cv_data.mobile or self.cv_data.phone, 10),
            (self.cv_data.summary, 15),
            (len(self.cv_data.experiences) > 0, 20),
            (len(self.cv_data.education) > 0, 15),
            (len(self.cv_data.skills) > 0, 10),
            (self.cv_data.linkedin_url, 5),
            (len(self.cv_data.languages) > 0, 5),
        ]
        
        for field, points in fields:
            if field:
                score += points
        
        self.cv_data.confidence_score = min(score, 100)
