"""
Tests para el servicio JobProfileExtractor
"""
import pytest
import tempfile
import os
from pathlib import Path

from app.services.job_profile_extractor import JobProfileExtractor, extract_job_profile


class TestJobProfileExtractor:
    """Tests para la clase JobProfileExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Fixture para crear instancia del extractor."""
        return JobProfileExtractor()
    
    @pytest.fixture
    def sample_profile_text(self):
        """Texto de ejemplo de un perfil de cargo."""
        return """
Director Administrativo y Financiero
NGDS | Perfil de Cargo | Version 1 | Enero 2026

Objetivo del Rol
Garantizar la sostenibilidad financiera y el orden administrativo de la organización mediante la gestión eficiente de recursos, procesos y equipos.

Estructura del Cargo
Personas a cargo: 1 Analista Financiero y de Nómina
Reporta a: CEO y Junta Directiva
Nivel: Dirección
Modalidad: Presencial

Responsabilidades por Frente
Financieras:
- Liderar la gestión financiera integral: P&L, flujo de caja y estados financieros
- Evaluar la viabilidad financiera de proyectos y propuestas comerciales
- Gestionar relaciones con entidades bancarias y financieras

Tesorería y Administrativas:
- Gestionar tesorería diaria, pagos a proveedores y conciliaciones bancarias
- Ejecutar y controlar el proceso de nómina completo
- Supervisar la gestión documental y archivo

Perfil Requerido
Formación: Profesional en Finanzas, Administración de Empresas, Contaduría Pública o carreras afines. Especialización o Maestría deseable.
Tiempo de Experiencia: Mínimo 8-10 años en roles financieros, de los cuales al menos 3 en posiciones de dirección.

Perfil DISC Esperado
Concienzudo + Dominante (C + D) o Concienzudo + Influyente (C + I)

Conocimientos Técnicos:
1. Gestión financiera integral y análisis de estados financieros
2. Modelación financiera avanzada en Excel
3. Normativa contable NIIF y tributaria
4. Manejo de ERP financiero (SAP, Oracle o similar)
5. Inglés técnico avanzado

Competencias Clave:
- Criterio financiero orientado a negocio
- Autonomía y responsabilidad
- Sentido de urgencia
- Comunicación efectiva
- Liderazgo de equipos

Herramientas:
- Excel avanzado (tablas dinámicas, macros)
- SAP / Oracle ERP
- Power BI
- Office 365

Condiciones
Salario: A convenir según experiencia
Ubicación: Bogotá, Colombia
Beneficios: Seguro médico, bonificación por desempeño
"""
    
    def test_clean_text(self, extractor):
        """Test para la limpieza de texto."""
        dirty_text = """Línea 1\r\nLínea 2   con   espacios\n\n\n\nLínea 3\nPágina 1\nhttps://ejemplo.com\n"""
        
        cleaned = extractor._clean_text(dirty_text)
        
        assert "\r" not in cleaned
        assert "  " not in cleaned or cleaned.count("\n") < 5
        assert "https://" not in cleaned
    
    def test_extract_role_title(self, extractor, sample_profile_text):
        """Test para extraer el título del cargo."""
        title = extractor._extract_role_title(sample_profile_text)
        
        assert "Director Administrativo y Financiero" in title
        assert "NGDS" not in title
        assert "Version" not in title
    
    def test_extract_role_title_simple(self, extractor):
        """Test para extraer título sin metadatos."""
        simple_text = """Gerente de Ventas

Objetivo del Rol
..."""
        title = extractor._extract_role_title(simple_text)
        assert "Gerente de Ventas" == title
    
    def test_identify_sections(self, extractor, sample_profile_text):
        """Test para identificar secciones del documento."""
        sections = extractor._identify_sections(sample_profile_text)
        
        assert "objetivo" in sections
        assert "estructura" in sections
        assert "responsabilidades" in sections
        assert "perfil" in sections
        assert "disc" in sections
        assert "conocimientos" in sections
        assert "competencias" in sections
        assert "herramientas" in sections
        assert "condiciones" in sections
    
    def test_parse_objective(self, extractor, sample_profile_text):
        """Test para parsear el objetivo del rol."""
        sections = extractor._identify_sections(sample_profile_text)
        objective = extractor._parse_objective(sections.get("objetivo", ""))
        
        assert "sostenibilidad financiera" in objective
        assert len(objective) > 20
    
    def test_parse_hierarchy(self, extractor, sample_profile_text):
        """Test para parsear la estructura/jerarquía."""
        sections = extractor._identify_sections(sample_profile_text)
        hierarchy = extractor._parse_hierarchy(sections.get("estructura", ""))
        
        assert "CEO y Junta Directiva" in hierarchy["reports_to"]
        assert "Dirección" in hierarchy["level"]
        assert "1 Analista Financiero" in hierarchy["direct_reports"]
        assert "Presencial" in hierarchy["work_mode"]
    
    def test_parse_responsibilities(self, extractor, sample_profile_text):
        """Test para parsear responsabilidades."""
        sections = extractor._identify_sections(sample_profile_text)
        responsibilities = extractor._parse_responsibilities(
            sections.get("responsabilidades", "")
        )
        
        assert len(responsibilities) > 0
        # Debe tener categorías
        assert any("Financieras" in cat for cat in responsibilities.keys()) or \
               any("Tesorería" in cat for cat in responsibilities.keys())
    
    def test_parse_requirements(self, extractor, sample_profile_text):
        """Test para parsear requisitos."""
        sections = extractor._identify_sections(sample_profile_text)
        requirements = extractor._parse_requirements(sections.get("perfil", ""))
        
        assert "Profesional en Finanzas" in requirements["education"]
        assert "8-10 años" in requirements["experience_years"]
    
    def test_parse_skills(self, extractor, sample_profile_text):
        """Test para parsear skills."""
        sections = extractor._identify_sections(sample_profile_text)
        skills = extractor._parse_skills(
            sections.get("conocimientos", ""),
            sections.get("competencias", ""),
            sections.get("perfil", "")
        )
        
        assert len(skills["technical"]) > 0
        assert len(skills["soft"]) > 0
        assert any("Excel" in skill for skill in skills["technical"])
    
    def test_parse_disc(self, extractor, sample_profile_text):
        """Test para parsear perfil DISC."""
        sections = extractor._identify_sections(sample_profile_text)
        disc = extractor._parse_disc(sections.get("disc", ""))
        
        assert "Concienzudo" in disc
        assert "Dominante" in disc or "Influyente" in disc
    
    def test_parse_tools(self, extractor, sample_profile_text):
        """Test para parsear herramientas."""
        sections = extractor._identify_sections(sample_profile_text)
        tools = extractor._parse_tools(sections.get("herramientas", ""))
        
        assert len(tools) > 0
        assert any("Excel" in tool for tool in tools)
    
    def test_parse_conditions(self, extractor, sample_profile_text):
        """Test para parsear condiciones."""
        sections = extractor._identify_sections(sample_profile_text)
        conditions = extractor._parse_conditions(sections.get("condiciones", ""))
        
        assert "Bogotá" in conditions["location"]
    
    def test_parse_job_profile_complete(self, extractor, sample_profile_text):
        """Test de integración para parsear perfil completo."""
        result = extractor.parse_job_profile(sample_profile_text)
        
        assert result["role_title"] is not None
        assert result["objective"] is not None
        assert result["hierarchy"] is not None
        assert result["responsibilities"] is not None
        assert result["requirements"] is not None
        assert result["skills"] is not None
        assert result["disc_profile"] is not None
        assert result["tools"] is not None
        assert result["metadata"] is not None
        
        # Verificar que hay secciones encontradas
        assert len(result["metadata"]["sections_found"]) > 0
    
    def test_extract_bullets(self, extractor):
        """Test para extraer bullets de una lista."""
        text = """
- Item 1
• Item 2
* Item 3
1. Item 4
2) Item 5
"""
        bullets = extractor._extract_bullets(text)
        
        assert len(bullets) == 5
        assert "Item 1" in bullets
        assert "Item 2" in bullets
    
    def test_clean_bullet_point(self, extractor):
        """Test para limpiar bullet points."""
        assert extractor._clean_bullet_point("- Item") == "Item"
        assert extractor._clean_bullet_point("• Item") == "Item"
        assert extractor._clean_bullet_point("1. Item") == "Item"
        assert extractor._clean_bullet_point("  Item  ") == "Item"


class TestExtractJobProfileIntegration:
    """Tests de integración con archivos reales."""
    
    @pytest.fixture
    def sample_txt_file(self):
        """Crear archivo TXT temporal."""
        content = """Analista de Datos Senior

Objetivo del Rol
Analizar datos para generar insights de negocio.

Estructura del Cargo
Reporta a: Gerente de Analytics
Nivel: Senior
Modalidad: Híbrido

Perfil Requerido
Formación: Ingeniería, Matemáticas, Estadística
Tiempo de Experiencia: 3-5 años

Conocimientos Técnicos:
- SQL avanzado
- Python para análisis de datos
- Tableau o Power BI
- Estadística aplicada
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        os.unlink(temp_path)
    
    def test_extract_from_txt(self, sample_txt_file):
        """Test para extraer desde archivo TXT."""
        result = extract_job_profile(sample_txt_file)
        
        assert result["role_title"] == "Analista de Datos Senior"
        assert "Gerente de Analytics" in result["hierarchy"]["reports_to"]
        assert "Senior" in result["hierarchy"]["level"]
        assert "SQL avanzado" in result["skills"]["technical"]
    
    def test_file_not_found(self):
        """Test para manejar archivo no encontrado."""
        with pytest.raises(FileNotFoundError):
            extract_job_profile("/ruta/que/no/existe.pdf")
    
    def test_unsupported_format(self, extractor):
        """Test para formato no soportado."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                extractor.extract_from_document(temp_path)
            
            assert "Formato no soportado" in str(exc_info.value)
        finally:
            os.unlink(temp_path)


class TestErrorHandling:
    """Tests para manejo de errores."""
    
    def test_empty_text(self, extractor):
        """Test para texto vacío."""
        result = extractor.parse_job_profile("")
        
        assert result["role_title"] == ""
        assert len(result["metadata"]["extraction_warnings"]) > 0
    
    def test_no_sections_found(self, extractor):
        """Test cuando no se encuentran secciones."""
        text = "Texto sin secciones identificables. Solo contenido libre."
        result = extractor.parse_job_profile(text)
        
        assert result["role_title"] != ""
        assert len(result["metadata"]["sections_found"]) == 0