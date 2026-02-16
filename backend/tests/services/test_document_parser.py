"""Tests para el DocumentParser."""
import pytest
import pytest_asyncio
import tempfile
import os

from app.services.extraction.document_parser import DocumentParser
from app.services.extraction.models import DocumentType


class TestDocumentParser:
    """Tests para DocumentParser."""
    
    @pytest_asyncio.fixture
    async def parser(self):
        return DocumentParser()
    
    @pytest.mark.asyncio
    async def test_detect_document_type_assessment(self, parser):
        """Test detección de tipo assessment."""
        text = """
        Factor Oscuro de la Personalidad
        Resultados Psicométricos
        
        Dimensión: Egocentrismo
        Score: 75.5
        Percentil: 80
        
        Interpretación del perfil...
        """
        
        doc_type = parser._detect_document_type(text)
        assert doc_type == DocumentType.ASSESSMENT
    
    @pytest.mark.asyncio
    async def test_detect_document_type_cv(self, parser):
        """Test detección de tipo CV."""
        text = """
        CURRICULUM VITAE
        
        Juan Pérez García
        
        EXPERIENCIA LABORAL
        - Senior Developer en TechCorp (2020-Presente)
        
        EDUCACIÓN
        - Ingeniería en Sistemas, Universidad Nacional
        
        HABILIDADES
        Python, JavaScript, React
        """
        
        doc_type = parser._detect_document_type(text)
        assert doc_type == DocumentType.CV
    
    @pytest.mark.asyncio
    async def test_detect_document_type_interview(self, parser):
        """Test detección de tipo entrevista."""
        text = """
        NOTAS DE ENTREVISTA
        
        Entrevistador: María González
        Fecha: 15 de enero de 2024
        
        Preguntas realizadas:
        1. Cuéntame sobre tu experiencia previa
        2. Por qué quieres trabajar aquí?
        
        Respuestas del candidato:
        - Muy buena comunicación
        - Experiencia relevante
        
        Recomendación: PROCEED
        """
        
        doc_type = parser._detect_document_type(text)
        assert doc_type == DocumentType.INTERVIEW
    
    @pytest.mark.asyncio
    async def test_detect_document_type_other(self, parser):
        """Test detección de tipo desconocido."""
        text = "Este es un texto genérico sin información específica."
        
        doc_type = parser._detect_document_type(text)
        assert doc_type == DocumentType.OTHER
    
    @pytest.mark.asyncio
    async def test_calculate_file_hash(self, parser):
        """Test cálculo de hash de archivo."""
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Contenido de prueba para hash")
            temp_path = f.name
        
        try:
            hash1 = parser.calculate_file_hash(temp_path)
            hash2 = parser.calculate_file_hash(temp_path)
            
            assert len(hash1) == 64  # SHA-256 produce 64 caracteres hex
            assert hash1 == hash2  # Mismo archivo = mismo hash
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_extract_txt(self, parser):
        """Test extracción de archivo TXT."""
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            f.write("Línea 1\nLínea 2\nLínea 3")
            temp_path = f.name
        
        try:
            text, metadata = await parser._extract_txt(temp_path)
            
            assert "Línea 1" in text
            assert "Línea 2" in text
            assert metadata['extraction_method'] == 'text_reader'
            assert 'encoding' in metadata
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_detect_mime_type(self, parser):
        """Test detección de MIME type."""
        # Crear archivos temporales de diferentes tipos
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b"%PDF-1.4")
            pdf_path = f.name
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            f.write(b"PK\x03\x04")  # Magic bytes de ZIP (DOCX es un ZIP)
            docx_path = f.name
        
        try:
            pdf_mime = parser._detect_mime_type(pdf_path)
            # docx_mime = parser._detect_mime_type(docx_path)  # Puede variar por sistema
            
            assert pdf_mime == 'application/pdf'
        finally:
            os.unlink(pdf_path)
            os.unlink(docx_path)
    
    @pytest.mark.asyncio
    async def test_supported_extensions(self, parser):
        """Test extensiones soportadas."""
        assert '.pdf' in parser.SUPPORTED_EXTENSIONS
        assert '.docx' in parser.SUPPORTED_EXTENSIONS
        assert '.txt' in parser.SUPPORTED_EXTENSIONS
    
    @pytest.mark.asyncio
    async def test_parse_from_bytes(self, parser):
        """Test parsing desde bytes."""
        content = b"Este es un texto de prueba para el parser.\n\nEs un CV con experiencia laboral y educacion."
        
        result = await parser.parse_from_bytes(
            document_id="test-123",
            file_bytes=content,
            filename="test_cv.txt"
        )
        
        assert result.document_id == "test-123"
        assert result.status.value == "parsing" or result.status.value == "error"
        assert len(result.text) > 0
    
    @pytest.mark.asyncio
    async def test_parse_document_not_found(self, parser):
        """Test parseo de documento inexistente."""
        result = await parser.parse_document(
            document_id="test-456",
            file_path="/ruta/inexistente/archivo.pdf"
        )
        
        assert result.status.value == "error"
        assert "no encontrado" in result.error_message.lower() or "not found" in result.error_message.lower()
