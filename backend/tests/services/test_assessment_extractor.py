"""Tests para el AssessmentExtractor."""
import pytest
import pytest_asyncio

from app.services.extraction.assessment_extractor import AssessmentExtractor


class TestAssessmentExtractor:
    """Tests para AssessmentExtractor."""
    
    @pytest_asyncio.fixture
    async def extractor(self):
        return AssessmentExtractor()
    
    @pytest.mark.asyncio
    async def test_extract_from_dark_factor_sample(self, extractor):
        """Test extracción de Dark Factor Inventory."""
        sample_text = """
        Factor Oscuro de la Personalidad - Reporte Individual
        
        Candidato: Juan Pérez
        Fecha: 15/01/2024
        
        Resultados por Dimensión:
        
        Egocentrismo: 72.5
        Volatilidad: 45.0
        Sicopatía: 38.5
        Manuabilidad: 55.0
        Narcisismo: 60.0
        
        Sinceridad: 88.0
        
        Interpretación: Perfil dentro de rangos normales.
        """
        
        result = await extractor.extract_from_text(sample_text)
        
        assert result.test_name == "Dark Factor Inventory"
        assert result.candidate_name == "Juan Pérez"
        assert len(result.scores) >= 4
        assert result.sincerity_score == 88.0
    
    @pytest.mark.asyncio
    async def test_detect_test_name(self, extractor):
        """Test detección de nombre de prueba."""
        assert extractor._detect_test_name("Factor Oscuro de la Personalidad") == "Dark Factor Inventory"
        assert extractor._detect_test_name("DISC Assessment Report") == "DISC Assessment"
        assert extractor._detect_test_name("Big Five Personality Test") == "Big Five Personality"
    
    @pytest.mark.asyncio
    async def test_extract_dimension_scores(self, extractor):
        """Test extracción de scores de dimensiones."""
        text = """
        Dimensión: Score
        Openness: 75.5
        Conscientiousness: 60.0
        Extraversion: 80.0
        Agreeableness: 65.0
        Neuroticism: 45.0
        """
        
        scores = extractor._extract_dimension_scores(text)
        
        assert len(scores) == 5
        
        # Verificar que se normalizaron los nombres
        score_names = [s.name for s in scores]
        assert "Openness" in score_names
        assert "Conscientiousness" in score_names
    
    @pytest.mark.asyncio
    async def test_extract_sincerity_score(self, extractor):
        """Test extracción de score de sinceridad."""
        text1 = "Sinceridad: 92.5"
        assert extractor._extract_sincerity_score(text1) == 92.5
        
        text2 = "Escala de Consistencia: 85"
        assert extractor._extract_sincerity_score(text2) == 85.0
        
        text3 = "Sin información de validez"
        assert extractor._extract_sincerity_score(text3) is None
    
    @pytest.mark.asyncio
    async def test_create_dimension(self, extractor):
        """Test creación de dimensión estandarizada."""
        dimension = extractor._create_dimension("Egocentrismo", 70.0)
        
        assert dimension.name == "Egocentrism"
        assert dimension.value == 70.0
        assert dimension.category == "dark_factor"
    
    @pytest.mark.asyncio
    async def test_categorize_dimension(self, extractor):
        """Test categorización de dimensiones."""
        assert extractor._categorize_dimension("Egocentrism") == "dark_factor"
        assert extractor._categorize_dimension("Dominance") == "disc"
        assert extractor._categorize_dimension("Openness") == "big5"
        assert extractor._categorize_dimension("Integration") == "cognitive"
        assert extractor._categorize_dimension("Unknown") == "other"
    
    @pytest.mark.asyncio
    async def test_empty_text_raises_error(self, extractor):
        """Test que texto vacío lanza error."""
        with pytest.raises(Exception):
            await extractor.extract_from_text("")
    
    @pytest.mark.asyncio
    async def test_extract_from_table_format(self, extractor):
        """Test extracción desde formato tabla."""
        text = """
        | Dimensión | Score |
        | Egocentrismo | 65.0 |
        | Narcisismo | 70.0 |
        | Sicopatía | 40.0 |
        """
        
        result = await extractor.extract_from_text(text)
        
        assert len(result.scores) >= 3
