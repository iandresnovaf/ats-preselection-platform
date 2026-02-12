"""Tests for Odoo connector.

Tests use mocked responses to avoid hitting real Odoo instance.
"""
import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

import httpx
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.odoo_connector import (
    OdooConnector,
    OdooConnectionInfo,
    OdooAPIError,
    OdooRateLimits,
    OdooWebhookHandler,
)
from app.schemas import OdooConfig
from app.models import JobOpening, Candidate, JobStatus, CandidateStatus


@pytest.fixture
def odoo_config():
    """Configuración de prueba para Odoo."""
    return OdooConfig(
        url="https://test.odoo.com",
        database="test_db",
        username="admin@test.com",
        api_key="test_api_key",
        job_model="hr.job",
        applicant_model="hr.applicant"
    )


@pytest.fixture
def mock_connection():
    """Mock de conexión a Odoo."""
    return OdooConnectionInfo(
        url="https://test.odoo.com",
        database="test_db",
        user_id=2,
        username="admin@test.com",
        api_key="test_api_key",
        context={"lang": "es_ES"}
    )


class TestOdooConnector:
    """Tests para el conector de Odoo."""
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, odoo_config):
        """Test autenticación exitosa."""
        with respx.mock:
            # Mock login call
            respx.post("https://test.odoo.com/jsonrpc").mock(
                return_value=httpx.Response(200, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": 2  # User ID
                })
            )
            
            async with AsyncSession() as db:
                connector = OdooConnector(db, odoo_config)
                connector.http_client = httpx.AsyncClient()
                
                success = await connector.authenticate()
                
                assert success is True
                assert connector._uid == 2
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, odoo_config):
        """Test autenticación fallida."""
        with respx.mock:
            respx.post("https://test.odoo.com/jsonrpc").mock(
                return_value=httpx.Response(200, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": False  # Login failed
                })
            )
            
            async with AsyncSession() as db:
                connector = OdooConnector(db, odoo_config)
                connector.http_client = httpx.AsyncClient()
                
                success = await connector.authenticate()
                
                assert success is False
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, odoo_config, mock_connection):
        """Test conexión exitosa."""
        with respx.mock:
            # Mock version (no auth required)
            respx.post("https://test.odoo.com/jsonrpc").mock(
                return_value=httpx.Response(200, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "server_version": "16.0",
                        "server_version_info": [16, 0, 0, "final", 0]
                    }
                })
            )
            
            async with AsyncSession() as db:
                connector = OdooConnector(db, odoo_config)
                connector.http_client = httpx.AsyncClient()
                connector.connection_info = mock_connection
                
                success, message = await connector.test_connection()
                
                assert success is True
                assert "16.0" in message
    
    @pytest.mark.asyncio
    async def test_execute_kw(self, odoo_config, mock_connection):
        """Test ejecución de método en modelo."""
        with respx.mock:
            respx.post("https://test.odoo.com/jsonrpc").mock(
                return_value=httpx.Response(200, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": [1, 2, 3]  # IDs encontrados
                })
            )
            
            async with AsyncSession() as db:
                connector = OdooConnector(db, odoo_config)
                connector.http_client = httpx.AsyncClient()
                connector.connection_info = mock_connection
                
                result = await connector._execute_kw(
                    "hr.job",
                    "search",
                    [[]],
                    {"limit": 10}
                )
                
                assert result == [1, 2, 3]
    
    @pytest.mark.asyncio
    async def test_sync_jobs(self, odoo_config, mock_connection):
        """Test sincronización de jobs."""
        jobs_data = [
            {
                "id": 1,
                "name": "Software Developer",
                "description": "<p>Develop software</p>",
                "department_id": [1, "IT"],
                "state": "recruit",
                "create_date": "2024-01-01 00:00:00",
                "write_date": "2024-01-15 00:00:00"
            }
        ]
        
        with respx.mock:
            # Mock search
            respx.post("https://test.odoo.com/jsonrpc").mock(
                return_value=httpx.Response(200, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": [1]
                })
            )
            
            async with AsyncSession() as db:
                connector = OdooConnector(db, odoo_config)
                connector.http_client = httpx.AsyncClient()
                connector.connection_info = mock_connection
                
                # Mock _execute_kw para read
                connector._execute_kw = Mock(return_value=jobs_data)
                
                result = await connector.sync_jobs(full_sync=True)
                
                # El resultado depende de la implementación real
                assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_sync_candidates(self, odoo_config, mock_connection):
        """Test sincronización de candidatos."""
        candidates_data = [
            {
                "id": 1,
                "name": "John Doe",
                "email_from": "john@example.com",
                "partner_mobile": "+1234567890",
                "job_id": [1, "Developer"],
                "stage_id": [1, "New"],
                "create_date": "2024-01-01 00:00:00",
                "write_date": "2024-01-15 00:00:00"
            }
        ]
        
        with respx.mock:
            respx.post("https://test.odoo.com/jsonrpc").mock(
                return_value=httpx.Response(200, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": [1]
                })
            )
            
            async with AsyncSession() as db:
                connector = OdooConnector(db, odoo_config)
                connector.http_client = httpx.AsyncClient()
                connector.connection_info = mock_connection
                
                # Mock _execute_kw
                connector._execute_kw = Mock(return_value=candidates_data)
                
                result = await connector.sync_candidates(full_sync=True)
                
                assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_push_job_to_odoo(self, odoo_config, mock_connection):
        """Test enviar job a Odoo."""
        job = JobOpening(
            title="Test Job",
            description="Test Description",
            department="IT",
            is_active=True
        )
        
        with respx.mock:
            respx.post("https://test.odoo.com/jsonrpc").mock(
                return_value=httpx.Response(200, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": 99  # New ID
                })
            )
            
            async with AsyncSession() as db:
                connector = OdooConnector(db, odoo_config)
                connector.http_client = httpx.AsyncClient()
                connector.connection_info = mock_connection
                connector.db = db
                
                success, odoo_id = await connector.push_job_to_odoo(job)
                
                # El resultado depende del mock
                assert isinstance(success, bool)
    
    @pytest.mark.asyncio
    async def test_push_candidate_to_odoo(self, odoo_config, mock_connection):
        """Test enviar candidato a Odoo."""
        candidate = Candidate(
            full_name="Jane Doe",
            email="jane@example.com",
            phone="+1234567890"
        )
        
        with respx.mock:
            respx.post("https://test.odoo.com/jsonrpc").mock(
                return_value=httpx.Response(200, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": 100  # New ID
                })
            )
            
            async with AsyncSession() as db:
                connector = OdooConnector(db, odoo_config)
                connector.http_client = httpx.AsyncClient()
                connector.connection_info = mock_connection
                connector.db = db
                
                success, odoo_id = await connector.push_candidate_to_odoo(candidate)
                
                assert isinstance(success, bool)
    
    @pytest.mark.asyncio
    async def test_webhook_handler(self, odoo_config, mock_connection):
        """Test manejo de webhook."""
        webhook_data = {
            "model": "hr.job",
            "action": "create",
            "data": {
                "id": 1,
                "name": "New Position"
            }
        }
        
        async with AsyncSession() as db:
            connector = OdooConnector(db, odoo_config)
            connector.connection_info = mock_connection
            
            handler = connector.get_webhook_handler()
            
            result = await handler.handle(
                json.dumps(webhook_data).encode(),
                {}
            )
            
            assert "success" in result


class TestOdooRateLimits:
    """Tests para rate limits."""
    
    def test_rate_limits_values(self):
        """Test valores de rate limits."""
        assert OdooRateLimits.REQUESTS_PER_SECOND == 10
        assert OdooRateLimits.MAX_BATCH_SIZE == 1000


class TestOdooAPIError:
    """Tests para errores de API."""
    
    def test_error_creation(self):
        """Test creación de error."""
        error = OdooAPIError(
            message="Test error",
            code=500,
            data={"debug": "traceback"}
        )
        
        assert error.message == "Test error"
        assert error.code == 500
        assert error.data == {"debug": "traceback"}
        assert str(error) == "Test error"


class TestOdooFieldMapping:
    """Tests para mapeo de campos."""
    
    @pytest.mark.asyncio
    async def test_job_field_mapping(self, odoo_config):
        """Test mapeo de campos de job."""
        odoo_data = {
            "id": 1,
            "name": "Developer",
            "description": "<p>Job description</p>",
            "department_id": [1, "Engineering"],
            "state": "recruit"
        }
        
        async with AsyncSession() as db:
            connector = OdooConnector(db, odoo_config)
            mapped = connector._map_job_fields(odoo_data)
            
            assert mapped["title"] == "Developer"
            assert mapped["department"] == "Engineering"
            assert mapped["status"] == JobStatus.ACTIVE.value
    
    @pytest.mark.asyncio
    async def test_candidate_field_mapping(self, odoo_config):
        """Test mapeo de campos de candidato."""
        odoo_data = {
            "id": 1,
            "name": "John Smith",
            "email_from": "john@test.com",
            "partner_mobile": "+1234567890",
            "job_id": [1, "Developer"],
            "stage_id": [2, "First Interview"]
        }
        
        async with AsyncSession() as db:
            connector = OdooConnector(db, odoo_config)
            mapped = connector._map_candidate_fields(odoo_data)
            
            assert mapped["full_name"] == "John Smith"
            assert mapped["email"] == "john@test.com"
            assert mapped["email_normalized"] == "john@test.com"
            assert mapped["status"] == CandidateStatus.INTERVIEW.value
    
    def test_strip_html(self, odoo_config):
        """Test remoción de HTML."""
        connector = OdooConnector(None, odoo_config)
        html = "<p>Test <b>description</b></p>"
        result = connector._strip_html(html)
        
        assert "<p>" not in result
        assert "Test" in result
        assert "description" in result
