"""Servicio de renderizado de plantillas de mensajes."""
import re
from typing import List, Dict, Set, Tuple

from app.models.message_templates import MessageTemplate


class TemplateRenderer:
    """Renderizador de plantillas con soporte para variables."""
    
    # Patrón para detectar variables: {variable_name}
    VARIABLE_PATTERN = re.compile(r'\{([a-z_][a-z0-9_]*)\}')
    
    def extract_variables(self, text: str) -> List[str]:
        """
        Extrae todas las variables del texto.
        
        Args:
            text: Texto que contiene variables en formato {variable_name}
            
        Returns:
            Lista de nombres de variables únicos encontrados
        """
        if not text:
            return []
        
        matches = self.VARIABLE_PATTERN.findall(text)
        # Eliminar duplicados manteniendo el orden
        seen = set()
        unique_vars = []
        for var in matches:
            if var not in seen:
                seen.add(var)
                unique_vars.append(var)
        return unique_vars
    
    def validate_variables(self, text: str, available_vars: List[str]) -> Tuple[bool, List[str]]:
        """
        Valida que todas las variables en el texto estén disponibles.
        
        Args:
            text: Texto con variables
            available_vars: Lista de variables disponibles
            
        Returns:
            Tuple de (es_válido, lista_de_variables_faltantes)
        """
        used_vars = self.extract_variables(text)
        available_set = set(available_vars)
        missing = [var for var in used_vars if var not in available_set]
        return len(missing) == 0, missing
    
    def render(self, template: MessageTemplate, variables: Dict[str, str]) -> Dict[str, any]:
        """
        Renderiza una plantilla reemplazando variables por valores reales.
        
        Args:
            template: Instancia de MessageTemplate
            variables: Diccionario de {nombre_variable: valor}
            
        Returns:
            Dict con subject, body, y metadatos del renderizado
        """
        # Extraer variables definidas en la plantilla
        template_vars = set(template.variables or [])
        
        # Extraer variables usadas en el body y subject
        body_vars = set(self.extract_variables(template.body))
        subject_vars = set(self.extract_variables(template.subject or ""))
        all_used_vars = body_vars | subject_vars
        
        # Renderizar body
        rendered_body = template.body
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            rendered_body = rendered_body.replace(placeholder, str(var_value))
        
        # Renderizar subject (si existe)
        rendered_subject = template.subject
        if rendered_subject:
            for var_name, var_value in variables.items():
                placeholder = f"{{{var_name}}}"
                rendered_subject = rendered_subject.replace(placeholder, str(var_value))
        
        # Identificar variables faltantes y extras
        provided_vars = set(variables.keys())
        missing_vars = list(all_used_vars - provided_vars)
        extra_vars = list(provided_vars - all_used_vars)
        
        return {
            "subject": rendered_subject,
            "body": rendered_body,
            "channel": template.channel.value,
            "rendered_variables": variables,
            "missing_variables": missing_vars,
            "extra_variables": extra_vars,
            "total_variables_found": len(all_used_vars),
            "variables_rendered": len(provided_vars & all_used_vars),
        }
    
    def render_text(self, text: str, variables: Dict[str, str]) -> str:
        """
        Renderiza texto simple reemplazando variables.
        
        Args:
            text: Texto con placeholders {variable}
            variables: Diccionario de valores
            
        Returns:
            Texto renderizado
        """
        if not text:
            return ""
        
        rendered = text
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            rendered = rendered.replace(placeholder, str(var_value))
        
        return rendered
    
    def preview(self, template: MessageTemplate, sample_variables: Dict[str, str]) -> Dict[str, any]:
        """
        Genera un preview de la plantilla con variables de ejemplo.
        
        Args:
            template: Instancia de MessageTemplate
            sample_variables: Variables de ejemplo para el preview
            
        Returns:
            Dict con el preview renderizado y metadatos
        """
        # Usar variables de ejemplo para las que no se proporcionaron
        preview_vars = {}
        
        # Extraer todas las variables usadas en el template
        body_vars = self.extract_variables(template.body)
        subject_vars = self.extract_variables(template.subject or "")
        all_vars = list(set(body_vars + subject_vars))
        
        for var in all_vars:
            if var in sample_variables:
                preview_vars[var] = sample_variables[var]
            else:
                preview_vars[var] = f"[{var}]"
        
        return self.render(template, preview_vars)
    
    def auto_detect_variables(self, text: str) -> List[str]:
        """
        Auto-detecta variables en un texto nuevo.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Lista de variables detectadas
        """
        return self.extract_variables(text)


# Instancia global del renderizador
template_renderer = TemplateRenderer()


def get_template_renderer() -> TemplateRenderer:
    """Obtiene la instancia del renderizador de plantillas."""
    return template_renderer
