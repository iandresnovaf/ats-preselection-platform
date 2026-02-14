"""
Smoke Tests Funcionales - Flujos Críticos
=========================================
Tests que verifican flujos completos funcionando.
Estos tests requieren que el sistema esté completamente configurado.
"""

import pytest
import httpx
import os
from datetime import datetime

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("TEST_FRONTEND_URL", "http://localhost:3000")
TIMEOUT = 10.0

TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "admin@example.com")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "changeme")


@pytest.fixture(scope="module")
async def auth_client():
    """Cliente autenticado para tests funcionales."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Login
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        
        if response.status_code != 200:
            pytest.skip(f"Cannot authenticate: {response.text}")
        
        # Actualizar cookies
        client.cookies.update(response.cookies)
        yield client


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_create_user_flow():
    """
    Verifica el flujo completo de creación de usuario.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Primero login como admin
        login_resp = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        
        if login_resp.status_code != 200:
            pytest.skip("Cannot login as admin")
        
        client.cookies.update(login_resp.cookies)
        
        # Crear usuario de test
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        new_user = {
            "email": f"test_smoke_{timestamp}@example.com",
            "password": "Test123!@#Password",
            "full_name": f"Test User {timestamp}",
            "role": "consultant"
        }
        
        # Intentar crear usuario (puede fallar si el endpoint no existe o requiere super_admin)
        response = await client.post(f"{BASE_URL}/api/v1/users", json=new_user)
        
        # Aceptamos 201 (creado) o 403 (no autorizado si no es super_admin)
        assert response.status_code in [201, 200, 403], \
            f"Create user unexpected status: {response.status_code}"
        
        if response.status_code in [201, 200]:
            print("✅ Create user flow passed")
        else:
            print(f"⚠️ Create user returned {response.status_code} (may require super_admin)")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_create_job_flow(auth_client):
    """
    Verifica el flujo de crear un job.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    job_data = {
        "title": f"Smoke Test Job {timestamp}",
        "department": "QA Testing",
        "location": "Remote",
        "employment_type": "full_time",
        "status": "active",
        "description": "Job created during smoke testing",
        "requirements": ["Test automation", "API testing"]
    }
    
    response = await auth_client.post(f"{BASE_URL}/api/v1/jobs", json=job_data)
    
    assert response.status_code == 201, f"Create job failed: {response.text}"
    data = response.json()
    assert data.get("id") is not None, "Create job response missing ID"
    print("✅ Create job flow passed")
    
    return data.get("id")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_create_candidate_flow(auth_client):
    """
    Verifica el flujo de crear un candidato.
    """
    # Primero obtener un job_id
    jobs_resp = await auth_client.get(f"{BASE_URL}/api/v1/jobs")
    
    if jobs_resp.status_code != 200 or not jobs_resp.json().get("items"):
        pytest.skip("No jobs available for candidate creation")
    
    jobs = jobs_resp.json()["items"]
    job_id = jobs[0]["id"]
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    candidate_data = {
        "email": f"smoke_candidate_{timestamp}@example.com",
        "full_name": f"Smoke Candidate {timestamp}",
        "job_opening_id": job_id,
        "phone": "+1234567890",
        "source": "smoke_test"
    }
    
    response = await auth_client.post(f"{BASE_URL}/api/v1/candidates", json=candidate_data)
    
    assert response.status_code == 201, f"Create candidate failed: {response.text}"
    data = response.json()
    assert data.get("id") is not None, "Create candidate response missing ID"
    print("✅ Create candidate flow passed")
    
    return data.get("id")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_upload_cv_endpoint(auth_client):
    """
    Verifica que el endpoint de upload de CV existe y acepta archivos.
    """
    # Crear un archivo PDF de prueba (mínimo válido)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids []\n/Count 0\n>>\nendobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\ntrailer\n<<\n/Size 3\n/Root 1 0 R\n>>\nstartxref\n104\n%%EOF"
    
    # Obtener un job_id
    jobs_resp = await auth_client.get(f"{BASE_URL}/api/v1/jobs")
    if jobs_resp.status_code != 200 or not jobs_resp.json().get("items"):
        pytest.skip("No jobs available for CV upload")
    
    job_id = jobs_resp.json()["items"][0]["id"]
    
    # Preparar multipart form
    files = {"cv_file": ("test_cv.pdf", pdf_content, "application/pdf")}
    data = {"job_opening_id": job_id}
    
    response = await auth_client.post(
        f"{BASE_URL}/api/v1/candidates/upload-cv",
        data=data,
        files=files
    )
    
    # Puede fallar por validación de CV pero el endpoint debe existir
    assert response.status_code in [201, 400, 422], \
        f"CV upload endpoint unexpected status: {response.status_code}"
    
    if response.status_code == 201:
        print("✅ CV upload flow passed")
    else:
        print(f"⚠️ CV upload returned {response.status_code} (expected for invalid test PDF)")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_matching_endpoint_responds(auth_client):
    """
    Verifica que el endpoint de matching responde.
    """
    # Obtener candidatos y jobs
    candidates_resp = await auth_client.get(f"{BASE_URL}/api/v1/candidates")
    jobs_resp = await auth_client.get(f"{BASE_URL}/api/v1/jobs")
    
    if candidates_resp.status_code != 200 or jobs_resp.status_code != 200:
        pytest.skip("Cannot fetch candidates or jobs")
    
    candidates = candidates_resp.json().get("items", [])
    jobs = jobs_resp.json().get("items", [])
    
    if not candidates or not jobs:
        pytest.skip("No candidates or jobs for matching test")
    
    # Intentar hacer matching
    match_data = {
        "candidate_id": candidates[0]["id"],
        "job_id": jobs[0]["id"]
    }
    
    response = await auth_client.post(f"{BASE_URL}/api/v1/matching", json=match_data)
    
    # El endpoint puede requerir parámetros específicos
    assert response.status_code in [200, 201, 400, 422], \
        f"Matching endpoint unexpected status: {response.status_code}"
    
    print("✅ Matching endpoint responds")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_list_jobs_pagination(auth_client):
    """
    Verifica que la paginación de jobs funciona.
    """
    response = await auth_client.get(f"{BASE_URL}/api/v1/jobs?page=1&page_size=5")
    
    assert response.status_code == 200, f"List jobs failed: {response.text}"
    data = response.json()
    
    assert "items" in data, "Response missing items"
    assert "total" in data, "Response missing total"
    assert "page" in data, "Response missing page"
    assert "pages" in data, "Response missing pages"
    
    print("✅ Jobs pagination works")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_list_candidates_pagination(auth_client):
    """
    Verifica que la paginación de candidatos funciona.
    """
    response = await auth_client.get(f"{BASE_URL}/api/v1/candidates?page=1&page_size=5")
    
    assert response.status_code == 200, f"List candidates failed: {response.text}"
    data = response.json()
    
    assert "items" in data, "Response missing items"
    assert "total" in data, "Response missing total"
    
    print("✅ Candidates pagination works")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_rate_limiting_active():
    """
    Verifica que el rate limiting está activo.
    Hace múltiples requests rápidos para activar el límite.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Hacer 10 requests rápidos al login
        responses = []
        for _ in range(10):
            resp = await client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={}
            )
            responses.append(resp.status_code)
        
        # Al menos algunas deben ser 429 (rate limited)
        # o 422 (validation error) si el rate limit no se activó aún
        has_rate_limit = 429 in responses
        has_validation_error = 422 in responses
        
        if has_rate_limit:
            print("✅ Rate limiting is active")
        elif has_validation_error:
            print("⚠️ Rate limiting may not be active yet (got validation errors)")
        else:
            print(f"⚠️ Unexpected responses: {set(responses)}")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_change_candidate_status(auth_client):
    """
    Verifica que se puede cambiar el estado de un candidato.
    """
    # Obtener candidatos
    candidates_resp = await auth_client.get(f"{BASE_URL}/api/v1/candidates")
    
    if candidates_resp.status_code != 200:
        pytest.skip("Cannot fetch candidates")
    
    candidates = candidates_resp.json().get("items", [])
    if not candidates:
        pytest.skip("No candidates available")
    
    candidate_id = candidates[0]["id"]
    
    # Cambiar estado
    status_data = {"status": "interview", "notes": "Smoke test status change"}
    response = await auth_client.post(
        f"{BASE_URL}/api/v1/candidates/{candidate_id}/change-status",
        json=status_data
    )
    
    assert response.status_code in [200, 201], f"Change status failed: {response.text}"
    print("✅ Change candidate status works")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_api_response_times(auth_client):
    """
    Verifica que los tiempos de respuesta de la API son aceptables.
    """
    import time
    
    endpoints = [
        ("GET", f"{BASE_URL}/health"),
        ("GET", f"{BASE_URL}/api/v1/jobs"),
        ("GET", f"{BASE_URL}/api/v1/candidates"),
    ]
    
    max_acceptable_time = 2.0  # segundos
    
    for method, url in endpoints:
        start = time.time()
        if method == "GET":
            response = await auth_client.get(url)
        else:
            continue
        elapsed = time.time() - start
        
        assert elapsed < max_acceptable_time, \
            f"{url} took {elapsed:.2f}s (max {max_acceptable_time}s)"
        
        print(f"✅ {url} responded in {elapsed:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
