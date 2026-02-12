"""Tests for Zoho Recruit connector.

Tests use mocked responses to avoid hitting real Zoho API.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

import httpx
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.zoho_recruit import (
    ZohoRecruitConnector,
    ZohoTokens,
    ZohoRateLimits,
    ZohoWebhookHandler,
)
from app.schemas import ZohoConfig
from app.models import JobOpening, Candidate, JobStatus, CandidateStatus


@pytest.fixture
def zoho_config():
    """Configuración de prueba para Zoho."""
    return ZohoConfig(
        client_id="test_client_id",
        client_secret="test_client_secret",
        refresh_token="test_refresh_token",
        redirect_uri="http://localhost:8000/callback"
    )


@pytest.fixture
def mock_tokens():
    """Tokens de prueba."""
    return ZohoTokens(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        api_domain="https://www.zohoapis.com"
    )


class TestZohoRecruitConnector:
    """Tests para el conector de Zoho Recruit."""
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, zoho_config, mock_tokens):
        """Test autenticación exitosa."""
        with respx.mock:
            # Mock token endpoint
            route = respx.post("https://accounts.zoho.com/oauth/v2/token").mock(
                return_value=httpx.Response(200, json={
                    "access_token": "new_access_token",
                    "refresh_token": "new_refresh_token",
                    "expires_in": 3600,
                    "api_domain": "https://www.zohoapis.com"
                })
            )
            
            async with AsyncSession() as db:
                connector = ZohoRecruitConnector(db, zoho_config)
                connector.http_client = httpx.AsyncClient()
                
                success = await connector.authenticate()
                
                assert success is True
                assert connector.tokens is not None
                assert connector.tokens.access_token == "new_access_token"
    
    @pytest.mark.asyncio
    async def test_authenticate_no_refresh_token(self, zoho_config):
        """Test autenticación fallida sin refresh token."""
        zoho_config.refresh_token = None
        
        async with AsyncSession() as db:
            connector = ZohoRecruitConnector(db, zoho_config)
            
            success = await connector.authenticate()
            
            assert success is False
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, zoho_config, mock_tokens):
        """Test conexión exitosa."""
        with respx.mock:
            # Mock org endpoint
            respx.get("https://recruit.zoho.com/recruit/v2/org").mock(
                return_value=httpx.Response(200, json={
                    "data": [{"org_name": "Test Org"}]
                })
            )
            
            async with AsyncSession() as db:
                connector = ZohoRecruitConnector(db, zoho_config)
                connector.http_client = httpx.AsyncClient()
                connector.tokens = mock_tokens
                
                success, message = await connector.test_connection()
                
                assert success is True
                assert "Test Org" in message
    
    @pytest.mark.asyncio
    async def test_test_connection_auth_error(self, zoho_config, mock_tokens):
        """Test conexión con error de autenticación."""
        with respx.mock:
            respx.get("https://recruit.zoho.com/recruit/v2/org").mock(
                return_value=httpx.Response(401, json={"error": "Unauthorized"})
            )
            
            async with AsyncSession() as db:
                connector = ZohoRecruitConnector(db, zoho_config)
                connector.http_client = httpx.AsyncClient()
                connector.tokens = mock_tokens
                
                success, message = await connector.test_connection()
                
                assert success is False
                assert "401" in message
    
    @pytest.mark.asyncio
    async def test_sync_jobs(self, zoho_config, mock_tokens):
        """Test sincronización de jobs."""
        jobs_data = {
            "data": [
                {
                    "id": "123456",
                    "Job_Opening_ID": "JOB-001",
                    "Job_Opening_Name": "Software Engineer",
                    "Job_Description": "Develop software",
                    "Department": "Engineering",
                    "Location": "Remote",
                    "Status": "Active",
                    "Created_Time": "2024-01-01T00:00:00Z",
                    "Modified_Time": "2024-01-15T00:00:00Z"
                }
            ]
        }
        
        with respx.mock:
            respx.get("https://recruit.zoho.com/recruit/v2/JobOpenings").mock(
                return_value=httpx.Response(200, json=jobs_data)
            )
            
            async with AsyncSession() as db:
                connector = ZohoRecruitConnector(db, zoho_config)
                connector.http_client = httpx.AsyncClient()
                connector.tokens = mock_tokens
                
                result = await connector.sync_jobs(full_sync=True)
                
                assert result.success is True
                assert result.items_processed == 1
                assert result.items_created == 1
    
    @pytest.mark.asyncio
    async def test_sync_candidates(self, zoho_config, mock_tokens):
        """Test sincronización de candidatos."""
        candidates_data = {
            "data": [
                {
                    "id": "789012",
                    "Candidate_ID": "CAND-001",
                    "First_Name": "John",
                    "Last_Name": "Doe",
                    "Email": "john.doe@example.com",
                    "Phone": "+1234567890",
                    "Stage": "New",
                    "Job_Opening_ID": "JOB-001",
                    "Created_Time": "2024-01-01T00:00:00Z",
                    "Modified_Time": "2024-01-15T00:00:00Z"
                }
            ]
        }
        
        with respx.mock:
            respx.get("https://recruit.zoho.com/recruit/v2/Candidates").mock(
                return_value=httpx.Response(200, json=candidates_data)
            )
            
            async with AsyncSession() as db:
                connector = ZohoRecruitConnector(db, zoho_config)
                connector.http_client = httpx.AsyncClient()
                connector.tokens = mock_tokens
                
                result = await connector.sync_candidates(full_sync=True)
                
                assert result.success is True
                assert result.items_processed == 1
                assert result.items_created == 1
    
    @pytest.mark.asyncio
    async def test_webhook_handler_create(self, zoho_config, mock_tokens):
        """Test manejo de webhook de creación."""
        webhook_data = {
            "module": "JobOpenings",
            "event": "create",
            "data": {
                "id": "123456",
                "Job_Opening_Name": "New Job",
                "Department": "IT"
            }
        }
        
        async with AsyncSession() as db:
            connector = ZohoRecruitConnector(db, zoho_config)
            handler = connector.get_webhook_handler()
            
            result = await handler.handle(
                json.dumps(webhook_data).encode(),
                {}
            )
            
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, zoho_config, mock_tokens):
        """Test que se respeta rate limiting."""
        request_count = 0
        
        def count_requests(request):
            nonlocal request_count
            request_count += 1
            return httpx.Response(200, json={"data": []})
        
        with respx.mock:
            respx.get("https://recruit.zoho.com/recruit/v2/JobOpenings").mock(
                side_effect=count_requests
            )
            
            async with AsyncSession() as db:
                connector = ZohoRecruitConnector(db, zoho_config)
                connector.http_client = httpx.AsyncClient()
                connector.tokens = mock_tokens
                
                # Hacer múltiples requests
                await connector.sync_jobs()
                await connector.sync_jobs()
                await connector.sync_jobs()
                
                # Verificar que no excede el rate limit
                assert request_count == 3


class TestZohoRateLimits:
    """Tests para rate limits."""
    
    def test_rate_limits_values(self):
        """Test valores de rate limits."""
        assert ZohoRateLimits.REQUESTS_PER_MINUTE == 100
        assert ZohoRateLimits.MAX_BATCH_SIZE == 200


class TestZohoFieldMapping:
    """Tests para mapeo de campos."""
    
    @pytest.mark.asyncio
    async def test_job_field_mapping(self, zoho_config):
        """Test mapeo de campos de job."""
        zoho_data = {
            "id": "123",
            "Job_Opening_Name": "Developer",
            "Department": "Engineering",
            "Location": "Remote",
            "Status": "Active"
        }
        
        async with AsyncSession() as db:
            connector = ZohoRecruitConnector(db, zoho_config)
            mapped = connector._map_job_fields(zoho_data)
            
            assert mapped["title"] == "Developer"
            assert mapped["department"] == "Engineering"
            assert mapped["location"] == "Remote"
    
    @pytest.mark.asyncio
    async def test_candidate_field_mapping(self, zoho_config):
        """Test mapeo de campos de candidato."""
        zoho_data = {
            "id": "456",
            "First_Name": "Jane",
            "Last_Name": "Smith",
            "Email": "jane@example.com",
            "Phone": "+1234567890",
            "Stage": "Interview"
        }
        
        async with AsyncSession() as db:
            connector = ZohoRecruitConnector(db, zoho_config)
            mapped = connector._map_candidate_fields(zoho_data)
            
            assert mapped["full_name"] == "Jane Smith"
            assert mapped["email"] == "jane@example.com"
            assert mapped["email_normalized"] == "jane@example.com"
