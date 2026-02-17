"""Tests para el servicio de renderizado de plantillas."""
import pytest
from app.models.message_templates import MessageTemplate, MessageChannel
from app.services.template_renderer import TemplateRenderer, template_renderer


class TestTemplateRenderer:
    """Tests para TemplateRenderer."""

    def test_extract_variables_simple(self):
        """Test extraer variables de texto simple."""
        text = "Hola {nombre}, bienvenido a {empresa}."
        renderer = TemplateRenderer()
        
        variables = renderer.extract_variables(text)
        
        assert variables == ["nombre", "empresa"]

    def test_extract_variables_repetidas(self):
        """Test que no duplica variables repetidas."""
        text = "Hola {nombre}, {nombre} bienvenido."
        renderer = TemplateRenderer()
        
        variables = renderer.extract_variables(text)
        
        assert variables == ["nombre"]

    def test_extract_variables_vacio(self):
        """Test con texto sin variables."""
        text = "Hola, bienvenido."
        renderer = TemplateRenderer()
        
        variables = renderer.extract_variables(text)
        
        assert variables == []

    def test_extract_variables_snake_case(self):
        """Test con variables en snake_case."""
        text = "Hola {candidate_name}, tu email es {candidate_email}."
        renderer = TemplateRenderer()
        
        variables = renderer.extract_variables(text)
        
        assert variables == ["candidate_name", "candidate_email"]

    def test_extract_variables_texto_vacio(self):
        """Test con texto vacío."""
        renderer = TemplateRenderer()
        
        variables = renderer.extract_variables("")
        
        assert variables == []

    def test_render_template_simple(self):
        """Test renderizado simple."""
        template = MessageTemplate(
            template_id=None,
            name="Test",
            channel=MessageChannel.WHATSAPP,
            body="Hola {nombre}, bienvenido a {empresa}.",
            variables=["nombre", "empresa"],
        )
        renderer = TemplateRenderer()
        
        result = renderer.render(template, {"nombre": "Juan", "empresa": "TechCorp"})
        
        assert result["body"] == "Hola Juan, bienvenido a TechCorp."

    def test_render_template_con_subject(self):
        """Test renderizado con subject (email)."""
        template = MessageTemplate(
            template_id=None,
            name="Test",
            channel=MessageChannel.EMAIL,
            subject="Oportunidad: {role_title}",
            body="Hola {candidate_name}, te contactamos sobre {role_title}.",
            variables=["role_title", "candidate_name"],
        )
        renderer = TemplateRenderer()
        
        result = renderer.render(template, {
            "role_title": "Desarrollador",
            "candidate_name": "María"
        })
        
        assert result["subject"] == "Oportunidad: Desarrollador"
        assert result["body"] == "Hola María, te contactamos sobre Desarrollador."

    def test_render_variables_faltantes(self):
        """Test detecta variables faltantes."""
        template = MessageTemplate(
            template_id=None,
            name="Test",
            channel=MessageChannel.WHATSAPP,
            body="Hola {nombre}, tu email es {email}.",
            variables=["nombre", "email"],
        )
        renderer = TemplateRenderer()
        
        result = renderer.render(template, {"nombre": "Juan"})
        
        assert result["missing_variables"] == ["email"]

    def test_render_variables_extras(self):
        """Test detecta variables extras proporcionadas."""
        template = MessageTemplate(
            template_id=None,
            name="Test",
            channel=MessageChannel.WHATSAPP,
            body="Hola {nombre}.",
            variables=["nombre"],
        )
        renderer = TemplateRenderer()
        
        result = renderer.render(template, {"nombre": "Juan", "extra": "valor"})
        
        assert result["extra_variables"] == ["extra"]

    def test_render_preserve_formatting(self):
        """Test que preserva saltos de línea y espacios."""
        template = MessageTemplate(
            template_id=None,
            name="Test",
            channel=MessageChannel.WHATSAPP,
            body="Hola {nombre},\n\nBienvenido a {empresa}.\n\nSaludos,",
            variables=["nombre", "empresa"],
        )
        renderer = TemplateRenderer()
        
        result = renderer.render(template, {"nombre": "Juan", "empresa": "Tech"})
        
        assert result["body"] == "Hola Juan,\n\nBienvenido a Tech.\n\nSaludos,"

    def test_render_text_simple(self):
        """Test renderizado de texto simple."""
        renderer = TemplateRenderer()
        
        result = renderer.render_text("Hola {name}", {"name": "World"})
        
        assert result == "Hola World"

    def test_render_text_multiple_occurrences(self):
        """Test renderizado con múltiples ocurrencias."""
        renderer = TemplateRenderer()
        
        result = renderer.render_text("{greet} {name}, {greet} again!", {
            "greet": "Hello",
            "name": "Juan"
        })
        
        assert result == "Hello Juan, Hello again!"

    def test_preview_usa_valores_ejemplo(self):
        """Test preview usa valores de ejemplo cuando no se proporcionan."""
        template = MessageTemplate(
            template_id=None,
            name="Test",
            channel=MessageChannel.WHATSAPP,
            body="Hola {nombre}, bienvenido.",
            variables=["nombre"],
        )
        renderer = TemplateRenderer()
        
        result = renderer.preview(template, {})
        
        assert result["body"] == "Hola [nombre], bienvenido."

    def test_preview_mezcla_valores(self):
        """Test preview mezcla valores proporcionados con placeholders."""
        template = MessageTemplate(
            template_id=None,
            name="Test",
            channel=MessageChannel.WHATSAPP,
            body="Hola {nombre}, tu rol es {role}.",
            variables=["nombre", "role"],
        )
        renderer = TemplateRenderer()
        
        result = renderer.preview(template, {"nombre": "Juan"})
        
        assert result["body"] == "Hola Juan, tu rol es [role]."

    def test_validate_variables_ok(self):
        """Test validación exitosa."""
        renderer = TemplateRenderer()
        
        is_valid, missing = renderer.validate_variables(
            "Hola {nombre}", 
            ["nombre", "apellido"]
        )
        
        assert is_valid is True
        assert missing == []

    def test_validate_variables_faltantes(self):
        """Test validación detecta variables faltantes."""
        renderer = TemplateRenderer()
        
        is_valid, missing = renderer.validate_variables(
            "Hola {nombre} {apellido}", 
            ["nombre"]
        )
        
        assert is_valid is False
        assert missing == ["apellido"]

    def test_auto_detect_variables(self):
        """Test auto-detección de variables."""
        renderer = TemplateRenderer()
        
        variables = renderer.auto_detect_variables("Contactar a {candidate} para {role}")
        
        assert variables == ["candidate", "role"]


class TestTemplateRendererGlobal:
    """Tests para la instancia global."""

    def test_global_instance_exists(self):
        """Test que existe la instancia global."""
        assert template_renderer is not None
        assert isinstance(template_renderer, TemplateRenderer)

    def test_get_template_renderer(self):
        """Test función helper get_template_renderer."""
        from app.services.template_renderer import get_template_renderer
        
        renderer = get_template_renderer()
        
        assert renderer is template_renderer
