"""Tests for LinkedIn connector.

Tests use mocked responses to avoid hitting real LinkedIn API.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import httpx
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.linkedin import (
    LinkedInConnector,
    LinkedInProfile,
    LinkedInTokens,
    LinkedInRateLimits,
)
from app.models import Candidate


@pytest.fixture
def linkedin_credentials():
    """Credenciales de prueba para LinkedIn."""
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "redirect_uri": "http://localhost:8000/callback"
    }


@pytest.fixture
def mock_tokens():
    """Tokens de prueba."""
    return LinkedInTokens(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        scope="r_liteprofile r_emailaddress r_basicprofile"
    )


class TestLinkedInConnector:
    """Tests para el conector de LinkedIn."""
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, linkedin_credentials):
        """Test autenticación exitosa con tokens en cache."""
        async with AsyncSession() as db:
            connector = LinkedInConnector(
                db,
                linkedin_credentials["client_id"],
                linkedin_credentials["client_secret"],
                linkedin_credentials["redirect_uri"]
            )
            
            # Mock cache con tokens válidos
            connector._set_cached = Mock(return_value=None)
            connector._get_cached = Mock(return_value={
                "access_token": "cached_token",
                "refresh_token": "cached_refresh",
                "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                "scope": "r_liteprofile"
            })
            
            success = await connector.authenticate()
            
            assert success is True
            assert connector.tokens is not None
    
    @pytest.mark.asyncio
    async def test_authenticate_no_tokens(self, linkedin_credentials):
        """Test autenticación sin tokens."""
        async with AsyncSession() as db:
            connector = LinkedInConnector(
                db,
                linkedin_credentials["client_id"],
                linkedin_credentials["client_secret"]
            )
            
            connector._get_cached = Mock(return_value=None)
            
            success = await connector.authenticate()
            
            assert success is False
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, linkedin_credentials, mock_tokens):
        """Test conexión exitosa."""
        with respx.mock:
            respx.get("https://api.linkedin.com/v2/me").mock(
                return_value=httpx.Response(200, json={
                    "id": "test_id",
                    "firstName": {
                        "localized": {"en_US": "John"}
                    },
                    "lastName": {
                        "localized": {"en_US": "Doe"}
                    }
                })
            )
            
            async with AsyncSession() as db:
                connector = LinkedInConnector(
                    db,
                    linkedin_credentials["client_id"],
                    linkedin_credentials["client_secret"]
                )
                connector.http_client = httpx.AsyncClient()
                connector.tokens = mock_tokens
                
                success, message = await connector.test_connection()
                
                assert success is True
                assert "John" in message
    
    @pytest.mark.asyncio
    async def test_test_connection_auth_error(self, linkedin_credentials, mock_tokens):
        """Test conexión con error 401."""
        with respx.mock:
            respx.get("https://api.linkedin.com/v2/me").mock(
                return_value=httpx.Response(401, json={"error": "Unauthorized"})
            )
            
            async with AsyncSession() as db:
                connector = LinkedInConnector(
                    db,
                    linkedin_credentials["client_id"],
                    linkedin_credentials["client_secret"]
                )
                connector.http_client = httpx.AsyncClient()
                connector.tokens = mock_tokens
                
                success, message = await connector.test_connection()
                
                assert success is False
                assert "401" in message
    
    def test_get_auth_url(self, linkedin_credentials):
        """Test generación de URL de autorización."""
        async def test():
            async with AsyncSession() as db:
                connector = LinkedInConnector(
                    db,
                    linkedin_credentials["client_id"],
                    linkedin_credentials["client_secret"],
                    linkedin_credentials["redirect_uri"]
                )
                
                auth_url = connector.get_auth_url(state="test_state")
                
                assert "linkedin.com/oauth" in auth_url
                assert linkedin_credentials["client_id"] in auth_url
                assert "test_state" in auth_url
                assert "r_liteprofile" in auth_url
        
        import asyncio
        asyncio.run(test())
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self, linkedin_credentials):
        """Test intercambio de código por tokens."""
        with respx.mock:
            respx.post("https://www.linkedin.com/oauth/v2/accessToken").mock(
                return_value=httpx.Response(200, json={
                    "access_token": "new_access_token",
                    "refresh_token": "new_refresh_token",
                    "expires_in": 3600,
                    "scope": "r_liteprofile r_emailaddress"
                })
            )
            
            async with AsyncSession() as db:
                connector = LinkedInConnector(
                    db,
                    linkedin_credentials["client_id"],
                    linkedin_credentials["client_secret"]
                )
                connector.http_client = httpx.AsyncClient()
                
                success, data = await connector.exchange_code_for_tokens("test_code")
                
                assert success is True
                assert connector.tokens is not None
                assert connector.tokens.access_token == "new_access_token"
    
    @pytest.mark.asyncio
    async def test_get_profile(self, linkedin_credentials, mock_tokens):
        """Test obtención de perfil."""
        with respx.mock:
            # Mock profile endpoint
            respx.get("https://api.linkedin.com/v2/me").mock(
                return_value=httpx.Response(200, json={
                    "id": "linkedin_id_123",
                    "vanityName": "john-doe",
                    "firstName": {"localized": {"en_US": "John"}},
                    "lastName": {"localized": {"en_US": "Doe"}},
                    "headline": {"localized": {"en_US": "Software Engineer"}},
                    "summary": {"localized": {"en_US": "Experienced developer"}},
                    "industryName": "Technology",
                    "location": {"name": "San Francisco Bay Area"}
                })
            )
            
            # Mock email endpoint
            respx.get("https://api.linkedin.com/v2/emailAddress").mock(
                return_value=httpx.Response(200, json={
                    "elements": [{
                        "handle~": {"emailAddress": "john@example.com"}
                    }]
                })
            )
            
            async with AsyncSession() as db:
                connector = LinkedInConnector(
                    db,
                    linkedin_credentials["client_id"],
                    linkedin_credentials["client_secret"]
                )
                connector.http_client = httpx.AsyncClient()
                connector.tokens = mock_tokens
                
                profile = await connector.get_profile()
                
                assert profile is not None
                assert profile.first_name == "John"
                assert profile.last_name == "Doe"
                assert profile.full_name == "John Doe"
                assert profile.email == "john@example.com"
                assert profile.linkedin_url == "https://www.linkedin.com/in/john-doe"
    
    @pytest.mark.asyncio
    async def test_import_candidate_from_url(self, linkedin_credentials, mock_tokens):
        """Test importación de candidato desde URL."""
        with respx.mock:
            # Mock endpoints
            respx.get("https://api.linkedin.com/v2/me").mock(
                return_value=httpx.Response(200, json={
                    "id": "123",
                    "vanityName": "jane-doe",
                    "firstName": {"localized": {"en_US": "Jane"}},
                    "lastName": {"localized": {"en_US": "Doe"}},
                })
            )
            
            respx.get("https://api.linkedin.com/v2/emailAddress").mock(
                return_value=httpx.Response(200, json={
                    "elements": [{"handle~": {"emailAddress": "jane@example.com"}}]
                })
            )
            
            async with AsyncSession() as db:
                connector = LinkedInConnector(
                    db,
                    linkedin_credentials["client_id"],
                    linkedin_credentials["client_secret"]
                )
                connector.http_client = httpx.AsyncClient()
                connector.tokens = mock_tokens
                connector.db = db
                
                success, candidate, message = await connector.import_candidate_from_url(
                    "https://www.linkedin.com/in/jane-doe"
                )
                
                assert isinstance(success, bool)
                assert isinstance(message, str)
    
    def test_validate_linkedin_url(self, linkedin_credentials):
        """Test validación de URLs de LinkedIn."""
        async def test():
            async with AsyncSession() as db:
                connector = LinkedInConnector(
                    db,
                    linkedin_credentials["client_id"],
                    linkedin_credentials["client_secret"]
                )
                
                # URLs válidas
                assert connector._validate_linkedin_url("https://linkedin.com/in/john-doe") is True
                assert connector._validate_linkedin_url("https://www.linkedin.com/in/jane-doe") is True
                
                # URLs inválidas
                assert connector._validate_linkedin_url("https://linkedin.com/company/test") is False
                assert connector._validate_linkedin_url("https://example.com/in/test") is False
                assert connector._validate_linkedin_url("not-a-url") is False
        
        import asyncio
        asyncio.run(test())
    
    def test_extract_person_id_from_url(self, linkedin_credentials):
        """Test extracción de ID de URL."""
        async def test():
            async with AsyncSession() as db:
                connector = LinkedInConnector(
                    db,
                    linkedin_credentials["client_id"],
                    linkedin_credentials["client_secret"]
                )
                
                vanity = connector._extract_person_id_from_url("https://linkedin.com/in/john-doe")
                assert vanity == "john-doe"
                
                vanity = connector._extract_person_id_from_url("https://example.com/other")
                assert vanity is None
        
        import asyncio
        asyncio.run(test())


class TestLinkedInProfile:
    """Tests para LinkedInProfile."""
    
    def test_profile_creation(self):
        """Test creación de perfil."""
        profile = LinkedInProfile(
            linkedin_id="123",
            linkedin_url="https://linkedin.com/in/test",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            email="test@example.com",
            experience=[{"title": "Developer", "company": "Tech Co"}],
            education=[{"school": "University", "degree": "BS"}],
            skills=["Python", "JavaScript"]
        )
        
        assert profile.full_name == "Test User"
        assert len(profile.experience) == 1
        assert len(profile.skills) == 2
    
    def test_to_candidate_data(self):
        """Test conversión a datos de candidato."""
        profile = LinkedInProfile(
            linkedin_id="123",
            linkedin_url="https://linkedin.com/in/test",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            email="test@example.com",
            experience=[{"title": "Developer"}],
            education=[{"school": "University"}],
            skills=["Python"]
        )
        
        data = profile.to_candidate_data()
        
        assert data["full_name"] == "Test User"
        assert data["email"] == "test@example.com"
        assert data["linkedin_url"] == "https://linkedin.com/in/test"
        assert data["extracted_skills"] == ["Python"]
        assert "raw_data" in data


class TestLinkedInRateLimits:
    """Tests para rate limits."""
    
    def test_rate_limits_values(self):
        """Test valores de rate limits."""
        assert LinkedInRateLimits.REQUESTS_PER_DAY == 500
        assert LinkedInRateLimits.REQUESTS_PER_SECOND == 0.1
        assert LinkedInRateLimits.BURST_SIZE == 5


class TestLinkedInFieldParsing:
    """Tests para parsing de campos."""
    
    def test_get_localized_value(self, linkedin_credentials):
        """Test obtención de valores localizados."""
        async def test():
            async with AsyncSession() as db:
                connector = LinkedInConnector(
                    db,
                    linkedin_credentials["client_id"],
                    linkedin_credentials["client_secret"]
                )
                
                # Preferir español
                field = {"localized": {"es_ES": "Nombre", "en_US": "Name"}}
                assert connector._get_localized_value(field) == "Nombre"
                
                # Fallback a inglés
                field = {"localized": {"en_US": "Name"}}
                assert connector._get_localized_value(field) == "Name"
                
                # Campo vacío
                assert connector._get_localized_value({}) == ""
        
        import asyncio
        asyncio.run(test())
    
    def test_get_location(self, linkedin_credentials):
        """Test parsing de ubicación."""
        async def test():
            async with AsyncSession() as db:
                connector = LinkedInConnector(
                    db,
                    linkedin_credentials["client_id"],
                    linkedin_credentials["client_secret"]
                )
                
                # Con nombre
                location = {"name": "San Francisco"}
                assert connector._get_location(location) == "San Francisco"
                
                # Con país y ciudad
                location = {"country": "USA", "city": "NYC"}
                assert connector._get_location(location) == "USA, NYC"
                
                # Vacío
                assert connector._get_location({}) is None
        
        import asyncio
        asyncio.run(test())
    
    def test_parse_date(self, linkedin_credentials):
        """Test parsing de fechas."""
        async def test():
            async with AsyncSession() as db:
                connector = LinkedInConnector(
                    db,
                    linkedin_credentials["client_id"],
                    linkedin_credentials["client_secret"]
                )
                
                # Año y mes
                date = {"year": 2020, "month": 6}
                assert connector._parse_date(date) == "2020-06"
                
                # Solo año
                date = {"year": 2020}
                assert connector._parse_date(date) == "2020"
                
                # Vacío
                assert connector._parse_date(None) is None
        
        import asyncio
        asyncio.run(test())
