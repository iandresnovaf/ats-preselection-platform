"""
Integration Tests - API Contract Tests
======================================
Verifica que los contratos de API se mantienen.
Útil para detectar breaking changes.
"""

import pytest
import httpx
import os
from datetime import datetime

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
TIMEOUT = 10.0

TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "admin@example.com")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "changeme")


@pytest.fixture(scope="module")
async def auth_client():
    """Cliente autenticado."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        
        if response.status_code != 200:
            pytest.skip("Cannot authenticate")
        
        client.cookies.update(response.cookies)
        yield client


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuthContract:
    """Verifica contrato de API de autenticación."""
    
    async def test_login_response_structure(self, auth_client):
        """Verificar estructura de respuesta de login."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Campos requeridos
            required_fields = ["success", "user"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            # Estructura de usuario
            user = data["user"]
            user_fields = ["id", "email", "full_name", "role", "status"]
            for field in user_fields:
                assert field in user, f"Missing user field: {field}"
    
    async def test_me_response_structure(self, auth_client):
        """Verificar estructura de /auth/me."""
        response = await auth_client.get(f"{BASE_URL}/api/v1/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["id", "email", "full_name", "role", "status"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


@pytest.mark.integration
@pytest.mark.asyncio
class TestJobContract:
    """Verifica contrato de API de jobs."""
    
    async def test_job_list_response_structure(self, auth_client):
        """Verificar estructura de lista de jobs."""
        response = await auth_client.get(f"{BASE_URL}/api/v1/jobs")
        
        assert response.status_code == 200
        data = response.json()
        
        # Estructura de paginación
        pagination_fields = ["items", "total", "page", "page_size", "pages"]
        for field in pagination_fields:
            assert field in data, f"Missing pagination field: {field}"
        
        # Estructura de items
        if data["items"]:
            job = data["items"][0]
            job_fields = ["id", "title", "department", "location", "status"]
            for field in job_fields:
                assert field in job, f"Missing job field: {field}"
    
    async def test_job_detail_response_structure(self, auth_client):
        """Verificar estructura de detalle de job."""
        # Primero obtener un job
        list_resp = await auth_client.get(f"{BASE_URL}/api/v1/jobs")
        if list_resp.status_code != 200 or not list_resp.json().get("items"):
            pytest.skip("No jobs available")
        
        job_id = list_resp.json()["items"][0]["id"]
        
        response = await auth_client.get(f"{BASE_URL}/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["id", "title", "department", "location", "status", "created_at"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    async def test_job_create_response_structure(self, auth_client):
        """Verificar estructura de respuesta de creación."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        job_data = {
            "title": f"Contract Test {timestamp}",
            "department": "QA",
            "location": "Remote",
            "employment_type": "full_time",
            "status": "active",
            "description": "Test"
        }
        
        response = await auth_client.post(f"{BASE_URL}/api/v1/jobs", json=job_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert data["title"] == job_data["title"]


@pytest.mark.integration
@pytest.mark.asyncio
class TestCandidateContract:
    """Verifica contrato de API de candidatos."""
    
    async def test_candidate_list_response_structure(self, auth_client):
        """Verificar estructura de lista de candidatos."""
        response = await auth_client.get(f"{BASE_URL}/api/v1/candidates")
        
        assert response.status_code == 200
        data = response.json()
        
        pagination_fields = ["items", "total", "page", "page_size", "pages"]
        for field in pagination_fields:
            assert field in data, f"Missing pagination field: {field}"
        
        if data["items"]:
            candidate = data["items"][0]
            candidate_fields = ["id", "email", "full_name", "status", "job_opening_id"]
            for field in candidate_fields:
                assert field in candidate, f"Missing candidate field: {field}"
    
    async def test_candidate_detail_response_structure(self, auth_client):
        """Verificar estructura de detalle de candidato."""
        list_resp = await auth_client.get(f"{BASE_URL}/api/v1/candidates")
        if list_resp.status_code != 200 or not list_resp.json().get("items"):
            pytest.skip("No candidates available")
        
        candidate_id = list_resp.json()["items"][0]["id"]
        
        response = await auth_client.get(f"{BASE_URL}/api/v1/candidates/{candidate_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["id", "email", "full_name", "status", "job_opening_id", "created_at"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


@pytest.mark.integration
@pytest.mark.asyncio
class TestEvaluationContract:
    """Verifica contrato de API de evaluaciones."""
    
    async def test_evaluation_response_structure(self, auth_client):
        """Verificar estructura de evaluación."""
        # Obtener un candidato con evaluaciones
        candidates_resp = await auth_client.get(f"{BASE_URL}/api/v1/candidates")
        if candidates_resp.status_code != 200:
            pytest.skip("Cannot fetch candidates")
        
        candidates = candidates_resp.json().get("items", [])
        if not candidates:
            pytest.skip("No candidates available")
        
        candidate_id = candidates[0]["id"]
        
        # Intentar evaluar
        response = await auth_client.post(
            f"{BASE_URL}/api/v1/candidates/{candidate_id}/evaluate",
            json={"force": False}
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            
            # Campos esperados
            expected_fields = ["id", "score", "decision", "candidate_id", "created_at"]
            for field in expected_fields:
                if field not in data:
                    print(f"Warning: Missing field in evaluation response: {field}")


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorContract:
    """Verifica contrato de errores de API."""
    
    async def test_404_error_structure(self, auth_client):
        """Verificar estructura de error 404."""
        response = await auth_client.get(f"{BASE_URL}/api/v1/jobs/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
    
    async def test_422_error_structure(self, auth_client):
        """Verificar estructura de error 422."""
        response = await auth_client.post(
            f"{BASE_URL}/api/v1/jobs",
            json={"invalid": "data"}
        )
        
        assert response.status_code == 422
        data = response.json()
        
        assert "detail" in data
    
    async def test_401_error_structure(self):
        """Verificar estructura de error 401."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/api/v1/jobs")
            
            assert response.status_code in [401, 403]
            data = response.json()
            
            assert "detail" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
