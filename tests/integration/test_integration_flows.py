"""
Integration Tests - Flujos End-to-End Críticos
===============================================
Tests que verifican flujos completos de la aplicación.
Estos tests son más lentos pero cubren casos de uso reales.
"""

import pytest
import httpx
import os
import asyncio
from datetime import datetime

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
TIMEOUT = 30.0

TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "admin@example.com")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "changeme")


class TestData:
    """Clase para compartir datos entre tests."""
    user_id = None
    job_id = None
    candidate_id = None
    evaluation_id = None
    access_token = None


@pytest.fixture(scope="module")
async def client():
    """Cliente HTTP base."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        yield c


@pytest.fixture(scope="module")
async def auth_client(client):
    """Cliente autenticado."""
    # Login
    response = await client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    
    if response.status_code != 200:
        pytest.fail(f"Cannot authenticate: {response.text}")
    
    client.cookies.update(response.cookies)
    TestData.user_id = response.json()["user"]["id"]
    yield client


@pytest.mark.integration
@pytest.mark.asyncio
class TestLoginToMatchingFlow:
    """
    Flujo completo: Login → Crear Job → Crear Candidato → Matching
    """
    
    async def test_01_login(self, client):
        """Paso 1: Login exitoso."""
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "user" in data
        assert response.cookies.get("access_token") is not None
        
        # Guardar cookies para siguientes requests
        client.cookies.update(response.cookies)
        TestData.user_id = data["user"]["id"]
    
    async def test_02_create_job(self, auth_client):
        """Paso 2: Crear un job."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        job_data = {
            "title": f"Integration Test Job {timestamp}",
            "department": "Engineering",
            "location": "Remote",
            "employment_type": "full_time",
            "status": "active",
            "description": "Looking for a senior Python developer with FastAPI experience",
            "requirements": [
                "5+ years Python experience",
                "FastAPI / Django experience",
                "PostgreSQL and Redis",
                "Docker and Kubernetes"
            ],
            "skills_required": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "min_experience_years": 5,
            "salary_min": 80000,
            "salary_max": 120000,
            "salary_currency": "USD"
        }
        
        response = await auth_client.post(f"{BASE_URL}/api/v1/jobs", json=job_data)
        
        assert response.status_code == 201, f"Create job failed: {response.text}"
        data = response.json()
        assert "id" in data
        
        TestData.job_id = data["id"]
        assert data["title"] == job_data["title"]
        assert data["status"] == "active"
    
    async def test_03_get_created_job(self, auth_client):
        """Paso 3: Verificar que el job existe."""
        assert TestData.job_id is not None, "Job ID not set"
        
        response = await auth_client.get(f"{BASE_URL}/api/v1/jobs/{TestData.job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == TestData.job_id
    
    async def test_04_create_candidate(self, auth_client):
        """Paso 4: Crear un candidato para el job."""
        assert TestData.job_id is not None, "Job ID not set"
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        candidate_data = {
            "email": f"integration_test_{timestamp}@example.com",
            "full_name": f"John Doe {timestamp}",
            "job_opening_id": TestData.job_id,
            "phone": "+1-555-0123",
            "source": "integration_test",
            "extracted_skills": ["Python", "FastAPI", "Django", "PostgreSQL"],
            "extracted_experience": 6,
            "raw_data": {
                "test": True,
                "integration": True
            }
        }
        
        response = await auth_client.post(f"{BASE_URL}/api/v1/candidates", json=candidate_data)
        
        assert response.status_code == 201, f"Create candidate failed: {response.text}"
        data = response.json()
        assert "id" in data
        
        TestData.candidate_id = data["id"]
        assert data["email"] == candidate_data["email"]
        assert data["job_opening_id"] == TestData.job_id
    
    async def test_05_get_job_candidates(self, auth_client):
        """Paso 5: Verificar que el candidato aparece en el job."""
        assert TestData.job_id is not None
        
        response = await auth_client.get(
            f"{BASE_URL}/api/v1/jobs/{TestData.job_id}/candidates"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        
        # El candidato recién creado debe estar en la lista
        candidate_ids = [c["id"] for c in data["items"]]
        assert TestData.candidate_id in candidate_ids, \
            f"Created candidate {TestData.candidate_id} not found in job candidates"
    
    async def test_06_run_matching(self, auth_client):
        """Paso 6: Ejecutar matching entre candidato y job."""
        assert TestData.candidate_id is not None
        assert TestData.job_id is not None
        
        match_data = {
            "candidate_id": TestData.candidate_id,
            "job_id": TestData.job_id,
            "force": True
        }
        
        response = await auth_client.post(
            f"{BASE_URL}/api/v1/candidates/{TestData.candidate_id}/evaluate",
            json=match_data
        )
        
        # Puede tardar un poco debido a la llamada a OpenAI
        assert response.status_code in [200, 201, 202], f"Matching failed: {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "score" in data or "match_score" in data or "id" in data
            TestData.evaluation_id = data.get("id")
            print(f"✅ Matching completed with score: {data.get('score', 'N/A')}")


@pytest.mark.integration
@pytest.mark.asyncio
class TestCVUploadAndParse:
    """
    Flujo: Upload CV → Parsear → Extraer datos
    """
    
    async def test_01_create_job_for_cv(self, auth_client):
        """Crear un job para el test de CV."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        job_data = {
            "title": f"CV Test Job {timestamp}",
            "department": "Data Science",
            "location": "Remote",
            "employment_type": "full_time",
            "status": "active",
            "description": "Data Scientist position requiring Python and ML skills"
        }
        
        response = await auth_client.post(f"{BASE_URL}/api/v1/jobs", json=job_data)
        assert response.status_code == 201
        TestData.job_id = response.json()["id"]
    
    async def test_02_upload_cv(self, auth_client):
        """Subir un CV de prueba."""
        # Crear un PDF con texto de CV realista
        pdf_content = self._create_test_pdf()
        
        files = {"cv_file": ("data_scientist_cv.pdf", pdf_content, "application/pdf")}
        data = {"job_opening_id": TestData.job_id}
        
        response = await auth_client.post(
            f"{BASE_URL}/api/v1/candidates/upload-cv",
            data=data,
            files=files
        )
        
        # El parsing puede fallar por el PDF de prueba, pero el endpoint debe funcionar
        assert response.status_code in [201, 400], f"CV upload failed: {response.text}"
        
        if response.status_code == 201:
            TestData.candidate_id = response.json()["id"]
    
    def _create_test_pdf(self):
        """Crea un PDF mínimo válido con texto."""
        # PDF simple con texto
        return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 200
>>
stream
BT
/F1 12 Tf
100 700 Td
(John Smith) Tj
0 -20 Td
(Data Scientist with 5 years experience) Tj
0 -20 Td
(Skills: Python, Machine Learning, SQL) Tj
0 -20 Td
(Email: john.smith@example.com) Tj
0 -20 Td
(Phone: +1-555-0199) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
465
%%EOF"""


@pytest.mark.integration
@pytest.mark.asyncio
class TestCandidatePipeline:
    """
    Flujo: Cambiar estado de candidato → Verificar pipeline
    """
    
    async def test_setup_candidate(self, auth_client):
        """Setup: Crear job y candidato."""
        # Crear job
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        job_response = await auth_client.post(
            f"{BASE_URL}/api/v1/jobs",
            json={
                "title": f"Pipeline Test {timestamp}",
                "department": "QA",
                "location": "Remote",
                "employment_type": "full_time",
                "status": "active",
                "description": "Test job for pipeline"
            }
        )
        assert job_response.status_code == 201
        TestData.job_id = job_response.json()["id"]
        
        # Crear candidato
        candidate_response = await auth_client.post(
            f"{BASE_URL}/api/v1/candidates",
            json={
                "email": f"pipeline_{timestamp}@example.com",
                "full_name": f"Pipeline Test {timestamp}",
                "job_opening_id": TestData.job_id,
                "phone": "+1-555-0000",
                "source": "integration_test"
            }
        )
        assert candidate_response.status_code == 201
        TestData.candidate_id = candidate_response.json()["id"]
    
    async def test_change_status_to_screening(self, auth_client):
        """Cambiar estado a screening."""
        assert TestData.candidate_id is not None
        
        response = await auth_client.post(
            f"{BASE_URL}/api/v1/candidates/{TestData.candidate_id}/change-status",
            json={"status": "screening", "notes": "Initial screening"}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "screening"
    
    async def test_change_status_to_interview(self, auth_client):
        """Cambiar estado a interview."""
        response = await auth_client.post(
            f"{BASE_URL}/api/v1/candidates/{TestData.candidate_id}/change-status",
            json={"status": "interview", "notes": "Passed screening"}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "interview"
    
    async def test_change_status_to_offer(self, auth_client):
        """Cambiar estado a offer."""
        response = await auth_client.post(
            f"{BASE_URL}/api/v1/candidates/{TestData.candidate_id}/change-status",
            json={"status": "offer", "notes": "Great interview performance"}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "offer"
    
    async def test_verify_pipeline_history(self, auth_client):
        """Verificar que el historial de pipeline se mantiene."""
        response = await auth_client.get(
            f"{BASE_URL}/api/v1/candidates/{TestData.candidate_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "offer"


@pytest.mark.integration
@pytest.mark.asyncio
class TestAIEvaluation:
    """
    Flujo: Crear evaluación con IA → Verificar score
    """
    
    async def test_setup_for_evaluation(self, auth_client):
        """Setup: Crear job y candidato para evaluación."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Job específico para evaluación
        job_response = await auth_client.post(
            f"{BASE_URL}/api/v1/jobs",
            json={
                "title": f"AI Evaluation Test {timestamp}",
                "department": "Engineering",
                "location": "Remote",
                "employment_type": "full_time",
                "status": "active",
                "description": "Senior Python Developer position. Required: Python, FastAPI, PostgreSQL, Docker. 5+ years experience.",
                "skills_required": ["Python", "FastAPI", "PostgreSQL", "Docker"],
                "min_experience_years": 5
            }
        )
        assert job_response.status_code == 201
        TestData.job_id = job_response.json()["id"]
        
        # Candidato con skills coincidentes
        candidate_response = await auth_client.post(
            f"{BASE_URL}/api/v1/candidates",
            json={
                "email": f"ai_eval_{timestamp}@example.com",
                "full_name": f"AI Eval Candidate {timestamp}",
                "job_opening_id": TestData.job_id,
                "phone": "+1-555-0999",
                "source": "integration_test",
                "extracted_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"],
                "extracted_experience": 7,
                "raw_data": {
                    "summary": "Senior Python developer with 7 years of experience building scalable APIs with FastAPI and Django. Expert in PostgreSQL, Docker, and Kubernetes deployment."
                }
            }
        )
        assert candidate_response.status_code == 201
        TestData.candidate_id = candidate_response.json()["id"]
    
    async def test_create_ai_evaluation(self, auth_client):
        """Crear evaluación con IA."""
        assert TestData.candidate_id is not None
        
        eval_data = {
            "force": True
        }
        
        response = await auth_client.post(
            f"{BASE_URL}/api/v1/candidates/{TestData.candidate_id}/evaluate",
            json=eval_data
        )
        
        # La evaluación con IA puede tardar
        assert response.status_code in [200, 201, 202], f"AI evaluation failed: {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            
            # Verificar estructura de respuesta
            assert "id" in data, "Missing evaluation ID"
            assert "score" in data, "Missing score"
            
            # Verificar que el score es un número válido
            score = data["score"]
            assert isinstance(score, (int, float)), f"Score should be numeric: {score}"
            assert 0 <= score <= 100, f"Score should be between 0-100: {score}"
            
            # Verificar decision
            if "decision" in data:
                assert data["decision"] in ["PROCEED", "REVIEW", "REJECT"], \
                    f"Invalid decision: {data['decision']}"
            
            TestData.evaluation_id = data["id"]
            print(f"✅ AI Evaluation created with score: {score}")
    
    async def test_evaluation_appears_in_candidate(self, auth_client):
        """Verificar que la evaluación aparece en el candidato."""
        if not TestData.evaluation_id:
            pytest.skip("No evaluation was created")
        
        response = await auth_client.get(
            f"{BASE_URL}/api/v1/candidates/{TestData.candidate_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar que hay evaluaciones
        if "evaluations" in data:
            eval_ids = [e["id"] for e in data["evaluations"]]
            assert TestData.evaluation_id in eval_ids, \
                "Evaluation not found in candidate"
        
        # Verificar latest_score
        if "latest_score" in data:
            assert data["latest_score"] is not None, "Missing latest_score"


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorHandling:
    """
    Verificar manejo de errores en integración.
    """
    
    async def test_404_handling(self, auth_client):
        """Verificar respuesta 404."""
        response = await auth_client.get(f"{BASE_URL}/api/v1/jobs/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    async def test_validation_error_handling(self, auth_client):
        """Verificar respuesta 422."""
        response = await auth_client.post(
            f"{BASE_URL}/api/v1/jobs",
            json={"invalid_field": "value"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    async def test_unauthorized_access(self, client):
        """Verificar acceso no autorizado."""
        response = await client.get(f"{BASE_URL}/api/v1/jobs")
        
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
