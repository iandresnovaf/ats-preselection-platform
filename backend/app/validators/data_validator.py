"""Validadores de datos para el pipeline de documentos."""
import re
from datetime import datetime, date
from typing import Optional, Tuple, List
import logging

from app.services.extraction.models import ValidationError, ValidationResult

logger = logging.getLogger(__name__)


class DataValidator:
    """Validador de datos extraídos de documentos."""
    
    # Rangos válidos para scores
    SCORE_MIN = 0
    SCORE_MAX = 100
    
    # Patrón para validar emails
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    # Patrón para validar teléfonos E.164
    PHONE_PATTERN = re.compile(r'^\+[1-9]\d{1,14}$')
    
    # Formatos de fecha soportados
    DATE_FORMATS = [
        '%Y-%m-%d',
        '%Y-%m',
        '%Y',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%d-%m-%Y',
        '%m-%d-%Y',
        '%B %Y',
        '%b %Y',
        '%Y/%m/%d',
    ]
    
    def validate_score(self, value: float, dimension_name: str = "") -> Tuple[bool, Optional[str]]:
        """Valida que un score esté en el rango 0-100.
        
        Args:
            value: Valor a validar
            dimension_name: Nombre de la dimensión (para mensajes de error)
            
        Returns:
            Tuple (es_válido, mensaje_error)
        """
        if value is None:
            return False, f"Score{f' para {dimension_name}' if dimension_name else ''} no puede ser nulo"
        
        if not isinstance(value, (int, float)):
            return False, f"Score{f' para {dimension_name}' if dimension_name else ''} debe ser numérico"
        
        if not (self.SCORE_MIN <= value <= self.SCORE_MAX):
            return False, (
                f"Score{f' para {dimension_name}' if dimension_name else ''} "
                f"debe estar entre {self.SCORE_MIN} y {self.SCORE_MAX}"
            )
        
        return True, None
    
    def validate_phone(self, phone: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Valida y normaliza un número de teléfono.
        
        Args:
            phone: Número de teléfono a validar
            
        Returns:
            Tuple (es_válido, mensaje_error, teléfono_normalizado)
        """
        if not phone:
            return False, "Teléfono no puede estar vacío", None
        
        # Limpiar el número (quitar espacios, guiones, paréntesis)
        cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
        
        # Si no empieza con +, intentar agregar código de país por defecto
        if not cleaned.startswith('+'):
            # Si empieza con 00, reemplazar con +
            if cleaned.startswith('00'):
                cleaned = '+' + cleaned[2:]
            else:
                # Asumir que necesita código de país (por defecto +1 para US/CA)
                # Esto debería ser configurable por región
                cleaned = '+' + cleaned
        
        # Validar formato E.164
        if not self.PHONE_PATTERN.match(cleaned):
            return False, f"Formato de teléfono inválido: {phone}", None
        
        return True, None, cleaned
    
    def validate_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """Valida un email.
        
        Args:
            email: Email a validar
            
        Returns:
            Tuple (es_válido, mensaje_error)
        """
        if not email:
            return False, "Email no puede estar vacío"
        
        email = email.strip().lower()
        
        if not self.EMAIL_PATTERN.match(email):
            return False, f"Formato de email inválido: {email}"
        
        return True, None
    
    def validate_date(self, date_str: str) -> Tuple[bool, Optional[str], Optional[date]]:
        """Valida y parsea una fecha.
        
        Args:
            date_str: String de fecha a validar
            
        Returns:
            Tuple (es_válido, mensaje_error, fecha_parseada)
        """
        if not date_str:
            return False, "Fecha no puede estar vacía", None
        
        date_str = date_str.strip()
        
        # Manejar casos especiales
        if date_str.lower() in ['present', 'actual', 'current', 'now', 'hoy']:
            return True, None, date.today()
        
        # Intentar cada formato
        for fmt in self.DATE_FORMATS:
            try:
                parsed = datetime.strptime(date_str, fmt).date()
                return True, None, parsed
            except ValueError:
                continue
        
        return False, f"Formato de fecha no reconocido: {date_str}", None
    
    def validate_required_fields(
        self, 
        data: dict, 
        required_fields: List[str]
    ) -> List[ValidationError]:
        """Valida que los campos requeridos estén presentes.
        
        Args:
            data: Diccionario de datos
            required_fields: Lista de campos requeridos
            
        Returns:
            Lista de errores de validación
        """
        errors = []
        
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(ValidationError(
                    field=field,
                    message=f"Campo requerido: {field}",
                    severity="error"
                ))
            elif isinstance(data[field], str) and not data[field].strip():
                errors.append(ValidationError(
                    field=field,
                    message=f"Campo requerido no puede estar vacío: {field}",
                    severity="error"
                ))
        
        return errors
    
    def validate_assessment_data(self, data: dict) -> ValidationResult:
        """Valida datos de una prueba psicométrica.
        
        Args:
            data: Diccionario con datos de assessment
            
        Returns:
            Resultado de validación
        """
        errors = []
        warnings = []
        normalized = {}
        
        # Validar campos requeridos
        required = ['test_name', 'scores']
        errors.extend(self.validate_required_fields(data, required))
        
        # Validar scores
        scores = data.get('scores', [])
        if isinstance(scores, list):
            normalized_scores = []
            for score in scores:
                if isinstance(score, dict):
                    name = score.get('name', '')
                    value = score.get('value')
                    
                    is_valid, error_msg = self.validate_score(value, name)
                    if not is_valid:
                        errors.append(ValidationError(
                            field=f"score.{name}",
                            message=error_msg,
                            severity="error"
                        ))
                    else:
                        normalized_scores.append({
                            'name': name,
                            'value': float(value),
                            'description': score.get('description', ''),
                            'category': score.get('category', '')
                        })
            
            normalized['scores'] = normalized_scores
        
        # Validar sincerity_score si existe
        sincerity = data.get('sincerity_score')
        if sincerity is not None:
            is_valid, error_msg = self.validate_score(sincerity, 'sincerity_score')
            if not is_valid:
                warnings.append(ValidationError(
                    field='sincerity_score',
                    message=error_msg,
                    severity="warning"
                ))
            else:
                normalized['sincerity_score'] = float(sincerity)
        
        # Validar fechas
        test_date = data.get('test_date')
        if test_date:
            is_valid, error_msg, parsed_date = self.validate_date(test_date)
            if is_valid:
                normalized['test_date'] = parsed_date.isoformat()
            else:
                warnings.append(ValidationError(
                    field='test_date',
                    message=error_msg,
                    severity="warning"
                ))
        
        # Normalizar strings
        for field in ['test_name', 'test_type', 'candidate_name', 'interpretation']:
            if data.get(field):
                normalized[field] = str(data[field]).strip()
        
        # Validar que hay al menos un score
        if not normalized.get('scores'):
            errors.append(ValidationError(
                field='scores',
                message="Debe haber al menos una dimensión con score",
                severity="error"
            ))
        
        return ValidationResult(
            is_valid=len([e for e in errors if e.severity == "error"]) == 0,
            errors=errors,
            warnings=warnings,
            normalized_data=normalized
        )
    
    def validate_cv_data(self, data: dict) -> ValidationResult:
        """Valida datos de un CV.
        
        Args:
            data: Diccionario con datos de CV
            
        Returns:
            Resultado de validación
        """
        errors = []
        warnings = []
        normalized = {}
        
        # Validar email si existe
        email = data.get('email')
        if email:
            is_valid, error_msg = self.validate_email(email)
            if is_valid:
                normalized['email'] = email.strip().lower()
            else:
                warnings.append(ValidationError(
                    field='email',
                    message=error_msg,
                    severity="warning"
                ))
        
        # Validar teléfono si existe
        phone = data.get('phone')
        if phone:
            is_valid, error_msg, normalized_phone = self.validate_phone(phone)
            if is_valid:
                normalized['phone'] = normalized_phone
            else:
                warnings.append(ValidationError(
                    field='phone',
                    message=error_msg,
                    severity="warning"
                ))
        
        # Normalizar campos de texto
        text_fields = ['full_name', 'location', 'linkedin', 'summary']
        for field in text_fields:
            if data.get(field):
                normalized[field] = str(data[field]).strip()
        
        # Validar experiencia
        experience = data.get('experience', [])
        if isinstance(experience, list):
            normalized_exp = []
            for exp in experience:
                if isinstance(exp, dict):
                    norm_exp = {
                        'company': exp.get('company', '').strip() if exp.get('company') else None,
                        'title': exp.get('title', '').strip() if exp.get('title') else None,
                        'start_date': exp.get('start_date'),
                        'end_date': exp.get('end_date'),
                        'is_current': exp.get('is_current', False),
                        'description': exp.get('description', '').strip() if exp.get('description') else None,
                        'location': exp.get('location', '').strip() if exp.get('location') else None,
                    }
                    
                    # Validar fechas de experiencia
                    for date_field in ['start_date', 'end_date']:
                        if norm_exp[date_field]:
                            is_valid, error_msg, parsed_date = self.validate_date(norm_exp[date_field])
                            if is_valid:
                                norm_exp[date_field] = parsed_date.isoformat()
                            # No agregar error, solo warning para fechas
                    
                    normalized_exp.append(norm_exp)
            
            normalized['experience'] = normalized_exp
        
        # Validar educación
        education = data.get('education', [])
        if isinstance(education, list):
            normalized_edu = []
            for edu in education:
                if isinstance(edu, dict):
                    norm_edu = {
                        'institution': edu.get('institution', '').strip() if edu.get('institution') else None,
                        'degree': edu.get('degree', '').strip() if edu.get('degree') else None,
                        'field_of_study': edu.get('field_of_study', '').strip() if edu.get('field_of_study') else None,
                        'start_date': edu.get('start_date'),
                        'end_date': edu.get('end_date'),
                        'is_current': edu.get('is_current', False),
                    }
                    normalized_edu.append(norm_edu)
            
            normalized['education'] = normalized_edu
        
        # Normalizar listas
        for field in ['skills', 'languages', 'certifications']:
            items = data.get(field, [])
            if isinstance(items, list):
                normalized[field] = [str(item).strip() for item in items if item]
            elif isinstance(items, str):
                # Si viene como string separado por comas
                normalized[field] = [s.strip() for s in items.split(',') if s.strip()]
        
        # Validar que hay suficiente información
        if not normalized.get('full_name'):
            warnings.append(ValidationError(
                field='full_name',
                message="No se detectó el nombre completo",
                severity="warning"
            ))
        
        return ValidationResult(
            is_valid=len([e for e in errors if e.severity == "error"]) == 0,
            errors=errors,
            warnings=warnings,
            normalized_data=normalized
        )
    
    def validate_interview_data(self, data: dict) -> ValidationResult:
        """Valida datos de una entrevista.
        
        Args:
            data: Diccionario con datos de entrevista
            
        Returns:
            Resultado de validación
        """
        errors = []
        warnings = []
        normalized = {}
        
        # Normalizar campos de texto
        text_fields = ['interview_type', 'interviewer', 'summary', 'recommendation', 'overall_sentiment']
        for field in text_fields:
            if data.get(field):
                normalized[field] = str(data[field]).strip()
        
        # Validar fecha
        interview_date = data.get('date')
        if interview_date:
            is_valid, error_msg, parsed_date = self.validate_date(interview_date)
            if is_valid:
                normalized['date'] = parsed_date.isoformat()
            else:
                warnings.append(ValidationError(
                    field='date',
                    message=error_msg,
                    severity="warning"
                ))
        
        # Normalizar listas
        for field in ['flags', 'strengths', 'concerns']:
            items = data.get(field, [])
            if isinstance(items, list):
                normalized[field] = [str(item).strip() for item in items if item]
        
        # Normalizar citas clave
        quotes = data.get('key_quotes', [])
        if isinstance(quotes, list):
            normalized_quotes = []
            for quote in quotes:
                if isinstance(quote, dict):
                    normalized_quotes.append({
                        'text': str(quote.get('text', '')).strip(),
                        'category': quote.get('category'),
                        'sentiment': quote.get('sentiment')
                    })
                elif isinstance(quote, str):
                    normalized_quotes.append({
                        'text': quote.strip(),
                        'category': None,
                        'sentiment': None
                    })
            normalized['key_quotes'] = normalized_quotes
        
        return ValidationResult(
            is_valid=len([e for e in errors if e.severity == "error"]) == 0,
            errors=errors,
            warnings=warnings,
            normalized_data=normalized
        )
