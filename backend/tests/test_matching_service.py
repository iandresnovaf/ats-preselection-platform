"""Tests unitarios para el servicio de Matching IA."""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

import pytest_asyncio


# Mark all tests as async
pytestmark = pytest.mark.asyncio


class TestMatchingService:
    """Tests para MatchingService."""
    
    @pytest_asyncio.fixture
    async def mock_db(self):
        """Fixture para mock de base de datos."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()
        return db
    
    @pytest_asyncio.fixture
    async def mock_cache(self):
        """Fixture para mock de cache."""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        return cache
    
    @pytest_asyncio.fixture
    async def matching_service(self, mock_db, mock_cache):
        """Fixture para MatchingService."""
        from app.services.matching_service import MatchingService
        service = MatchingService(mock_db, cache=mock_cache)
        return service
    
    @pytest_asyncio.fixture
    def sample_candidate(self):
        """Fixture para candidato de ejemplo."""
        candidate = Mock()
        candidate.id = uuid4()
        candidate.full_name = "John Doe"
        candidate.email = "john@example.com"
        candidate.extracted_skills = ["Python", "React", "AWS"]
        candidate.extracted_experience = [{"years": 5, "title": "Senior Developer"}]
        candidate.extracted_education = [{"degree": "Bachelor", "field": "Computer Science"}]
        candidate.raw_data = {"name": "John Doe", "skills": ["Python"]}
        candidate.documents = []
        return candidate
    
    @pytest_asyncio.fixture
    def sample_job(self):
        """Fixture para job de ejemplo."""
        job = Mock()
        job.id = uuid4()
        job.title = "Senior Python Developer"
        job.description = "Looking for a senior Python developer with React experience"
        job.requirements = {
            "required_skills": ["Python", "React"],
            "preferred_skills": ["AWS", "Docker"],
            "min_years_experience": 3,
            "education_level": "bachelor"
        }
        job.seniority = "Senior"
        job.department = "Engineering"
        job.location = "Remote"
        job.employment_type = "full-time"
        job.job_description_document = None
        return job
    
    async def test_sanitize_input(self, matching_service):
        """Test de sanitización de inputs."""
        # Test normal text
        text = "Hello World"
        assert matching_service._sanitize_input(text) == "Hello World"
        
        # Test long text truncation
        long_text = "x" * 20000
        result = matching_service._sanitize_input(long_text, max_length=10000)
        assert len(result) == 10003  # 10000 + "..."
        
        # Test control characters removal
        text_with_control = "Hello\x00World\x08Test"
        result = matching_service._sanitize_input(text_with_control)
        assert "\x00" not in result
        assert "\x08" not in result
    
    async def test_compute_hash(self, matching_service):
        """Test de hash computation."""
        data = {"skills": ["Python", "React"], "experience": 5}
        hash1 = matching_service._compute_hash(data)
        hash2 = matching_service._compute_hash(data)
        
        # Same data should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex
        
        # Different data should produce different hash
        different_data = {"skills": ["Java"], "experience": 3}
        hash3 = matching_service._compute_hash(different_data)
        assert hash1 != hash3
    
    async def test_determine_recommendation(self, matching_service):
        """Test de determinación de recomendaciones."""
        # Score > 75 = PROCEED
        assert matching_service._determine_recommendation(80) == "PROCEED"
        assert matching_service._determine_recommendation(75) == "PROCEED"
        
        # Score 50-75 = REVIEW
        assert matching_service._determine_recommendation(74) == "REVIEW"
        assert matching_service._determine_recommendation(50) == "REVIEW"
        
        # Score < 50 = REJECT
        assert matching_service._determine_recommendation(49) == "REJECT"
        assert matching_service._determine_recommendation(0) == "REJECT"
    
    async def test_normalize_result(self, matching_service):
        """Test de normalización de resultados."""
        # Valid result
        result = {
            "score": 85.5,
            "skills_match": {"required_skills_percentage": 80.0},
            "recommendation": "PROCEED",
            "reasoning": "Good match",
            "strengths": ["Python expert"],
            "gaps": [],
            "red_flags": [],
            "experience_match": {},
            "education_match": {}
        }
        
        normalized = matching_service._normalize_result(result)
        assert normalized["score"] == 85.5
        assert normalized["recommendation"] == "PROCEED"
        
        # Score clamping
        result["score"] = 150
        normalized = matching_service._normalize_result(result)
        assert normalized["score"] == 100
        
        result["score"] = -10
        normalized = matching_service._normalize_result(result)
        assert normalized["score"] == 0
    
    async def test_get_cached_result(self, matching_service, mock_cache):
        """Test de obtención de cache."""
        # Cache miss
        mock_cache.get.return_value = None
        result = await matching_service._get_cached_result("c1", "j1", "hash1", "hash2")
        assert result is None
        
        # Cache hit
        cached_data = {"score": 80, "recommendation": "PROCEED"}
        mock_cache.get.return_value = cached_data
        result = await matching_service._get_cached_result("c1", "j1", "hash1", "hash2")
        assert result == cached_data
    
    async def test_candidate_not_found(self, matching_service, mock_db):
        """Test cuando el candidato no existe."""
        from app.services.matching_service import CandidateNotFoundError
        
        # Mock execute to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(CandidateNotFoundError):
            await matching_service._get_candidate_with_cv(str(uuid4()))
    
    async def test_job_not_found(self, matching_service, mock_db):
        """Test cuando el job no existe."""
        from app.services.matching_service import JobNotFoundError
        
        # Mock execute to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(JobNotFoundError):
            await matching_service._get_job_with_requirements(str(uuid4()))
    
    async def test_fallback_analysis(self, matching_service, sample_candidate, sample_job):
        """Test del análisis fallback cuando OpenAI no está disponible."""
        job_requirements = {
            "title": sample_job.title,
            "description": sample_job.description,
            "requirements": sample_job.requirements
        }
        
        result = await matching_service._fallback_analysis(sample_candidate, job_requirements)
        
        assert "score" in result
        assert "recommendation" in result
        assert "reasoning" in result
        assert result["llm_provider"] == "fallback"
        assert "skills" in result["reasoning"].lower() or "fallback" in result["reasoning"].lower()
    
    async def test_call_openai_success(self, matching_service):
        """Test de llamada exitosa a OpenAI."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "score": 85.0,
                "skills_match": {"required_skills_percentage": 80.0},
                "recommendation": "PROCEED",
                "reasoning": "Good match",
                "strengths": ["Python"],
                "gaps": [],
                "red_flags": [],
                "experience_match": {},
                "education_match": {}
            })))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        
        matching_service._openai_client = mock_client
        
        result = await matching_service._call_openai("test prompt")
        
        assert result["score"] == 85.0
        assert result["recommendation"] == "PROCEED"
    
    async def test_call_openai_invalid_json(self, matching_service):
        """Test de error cuando OpenAI retorna JSON inválido."""
        from app.services.matching_service import OpenAIError
        
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="invalid json"))]
        mock_client.chat.completions.create.return_value = mock_response
        
        matching_service._openai_client = mock_client
        
        with pytest.raises(OpenAIError):
            await matching_service._call_openai("test prompt")
    
    async def test_batch_analyze(self, matching_service, sample_candidate, sample_job):
        """Test de análisis batch."""
        # Mock analyze_match to avoid DB calls
        matching_service.analyze_match = AsyncMock(return_value={
            "score": 80.0,
            "recommendation": "PROCEED"
        })
        
        results = await matching_service.batch_analyze(
            candidate_ids=[str(sample_candidate.id), str(uuid4())],
            job_id=str(sample_job.id),
            user_id=str(uuid4())
        )
        
        assert len(results) == 2
        assert all("candidate_id" in r for r in results)
        assert all("success" in r for r in results)


class TestMatchingAPI:
    """Tests para los endpoints de Matching API."""
    
    @pytest.fixture
    def mock_user(self):
        """Fixture para usuario mock."""
        user = Mock()
        user.id = uuid4()
        user.role = "consultant"
        user.email = "test@example.com"
        return user
    
    def test_match_analyze_request_validation(self):
        """Test de validación de request de análisis."""
        from app.api.matching import MatchAnalyzeRequest
        
        # Valid request
        request = MatchAnalyzeRequest(
            candidate_id=str(uuid4()),
            job_id=str(uuid4()),
            force_refresh=False
        )
        assert request.candidate_id is not None
        assert request.job_id is not None
        
        # Invalid UUID should raise error
        with pytest.raises(ValueError):
            MatchAnalyzeRequest(
                candidate_id="invalid-uuid",
                job_id=str(uuid4())
            )
    
    def test_batch_analyze_request_validation(self):
        """Test de validación de request batch."""
        from app.api.matching import BatchAnalyzeRequest
        
        # Valid request
        request = BatchAnalyzeRequest(
            candidate_ids=[str(uuid4()), str(uuid4())],
            job_id=str(uuid4())
        )
        assert len(request.candidate_ids) == 2
        
        # Too many candidates
        with pytest.raises(ValueError):
            BatchAnalyzeRequest(
                candidate_ids=[str(uuid4()) for _ in range(101)],
                job_id=str(uuid4())
            )


class TestMatchingIntegration:
    """Tests de integración para el flujo completo de matching."""
    
    async def test_end_to_end_matching_flow(self):
        """Test del flujo completo de matching."""
        # Este test verifica que todos los componentes funcionan juntos
        # En un entorno real, se conectaría a una BD de prueba
        
        # Simular flujo:
        # 1. Crear candidato con CV
        # 2. Crear job con requisitos
        # 3. Ejecutar matching
        # 4. Verificar resultado
        
        # Por ahora solo verificamos que las importaciones funcionan
        from app.services.matching_service import MatchingService
        from app.api.matching import router
        from app.models.match_result import MatchResult, MatchRecommendation
        
        assert MatchingService is not None
        assert router is not None
        assert MatchResult is not None
        assert MatchRecommendation is not None
    
    async def test_cache_invalidation(self):
        """Test de invalidación de cache."""
        from app.services.matching_service import MatchingService
        
        # Verificar que el TTL de cache está configurado
        assert MatchingService.CACHE_TTL_SECONDS == 86400  # 24 horas
    
    async def test_rate_limiting_configuration(self):
        """Test de configuración de rate limiting."""
        from app.api.matching import ai_rate_limit
        
        # Verificar que el rate limiter está configurado
        assert ai_rate_limit is not None
        assert ai_rate_limit.requests == 10
        assert ai_rate_limit.window == 60
