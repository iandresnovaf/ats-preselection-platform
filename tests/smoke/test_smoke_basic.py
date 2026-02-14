"""
Smoke Tests para ATS Platform
=============================
Tests rápidos para verificar que todos los servicios críticos están funcionando.
Estos tests deben ejecutarse antes de cualquier deploy a producción.
"""

import pytest
import asyncio
import httpx
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from datetime import datetime

# Configuración
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("TEST_FRONTEND_URL", "http://localhost:3000")
DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/ats_db")
REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/0")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Timeout para tests
TIMEOUT = 10.0


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_backend_health_check():
    """
    Verifica que el endpoint de health check responde 200.
    Este es el test más crítico - si falla, el backend no está disponible.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}/health")
        
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy", f"Backend unhealthy: {data}"
        assert "database" in data.get("services", []), "Database not in healthy services"
        assert "redis" in data.get("services", []), "Redis not in healthy services"
        print("✅ Backend health check passed")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_database_connection():
    """
    Verifica conexión directa a PostgreSQL.
    Asegura que la base de datos está accesible y responde.
    """
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
            assert row[0] == 1, "Database query returned unexpected value"
        await engine.dispose()
        print("✅ Database connection passed")
    except Exception as e:
        pytest.fail(f"Database connection failed: {str(e)}")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_redis_connection():
    """
    Verifica conexión directa a Redis.
    Asegura que Redis está accesible y responde.
    """
    try:
        r = redis.from_url(REDIS_URL)
        pong = await r.ping()
        assert pong, "Redis ping failed"
        
        # Test set y get
        test_key = "smoke_test_key"
        test_value = f"test_{datetime.now().isoformat()}"
        await r.set(test_key, test_value, ex=10)
        retrieved = await r.get(test_key)
        assert retrieved == test_value, "Redis set/get failed"
        await r.delete(test_key)
        await r.close()
        print("✅ Redis connection passed")
    except Exception as e:
        pytest.fail(f"Redis connection failed: {str(e)}")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_openai_api_key():
    """
    Verifica que la API key de OpenAI es válida.
    Hace una llamada de prueba al endpoint de models.
    """
    if not OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY not set")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
            )
            assert response.status_code == 200, f"OpenAI API returned {response.status_code}"
            data = response.json()
            assert "data" in data, "OpenAI response missing 'data' field"
            # Verificar que gpt-4o-mini está disponible
            model_ids = [m["id"] for m in data.get("data", [])]
            assert "gpt-4o-mini" in model_ids or any("gpt-4" in m for m in model_ids), \
                "GPT-4 models not available"
        print("✅ OpenAI API key passed")
    except httpx.TimeoutException:
        pytest.fail("OpenAI API timeout - possible connectivity issue")
    except Exception as e:
        pytest.fail(f"OpenAI API key validation failed: {str(e)}")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_frontend_loads():
    """
    Verifica que el frontend carga sin errores.
    Busca el HTML básico y verifica que no hay errores JS críticos.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(FRONTEND_URL)
            assert response.status_code == 200, f"Frontend returned {response.status_code}"
            html = response.text
            
            # Verificar elementos básicos del HTML
            assert "<!DOCTYPE html>" in html or "<html" in html, "Invalid HTML response"
            assert "</html>" in html, "Incomplete HTML (missing closing tag)"
            assert "<script" in html, "No JavaScript files loaded"
            
            # Verificar que no hay mensajes de error críticos
            assert "Internal Server Error" not in html, "Frontend shows server error"
            assert "Runtime Error" not in html, "Frontend has runtime error"
            
        print("✅ Frontend load passed")
    except httpx.ConnectError:
        pytest.fail(f"Cannot connect to frontend at {FRONTEND_URL}")
    except Exception as e:
        pytest.fail(f"Frontend load failed: {str(e)}")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_api_docs_available():
    """
    Verifica que la documentación de API (Swagger) está disponible.
    Solo en modo DEBUG.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}/api/docs")
        # Puede ser 200 (si está habilitado) o 404 (si DEBUG=False)
        # Ambos son válidos dependiendo de la configuración
        if response.status_code == 200:
            assert "swagger" in response.text.lower() or "openapi" in response.text.lower(), \
                "API docs page doesn't contain swagger/openapi references"
            print("✅ API docs available (DEBUG mode)")
        else:
            print(f"⚠️ API docs returned {response.status_code} (may be disabled in production)")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_login_endpoint_exists():
    """
    Verifica que el endpoint de login existe y responde.
    No hace login real, solo verifica que el endpoint está disponible.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # POST sin credenciales debe devolver 422 (validation error)
        response = await client.post(f"{BASE_URL}/api/v1/auth/login", json={})
        assert response.status_code == 422, f"Login endpoint unexpected status: {response.status_code}"
        
        # Verificar que es un error de validación, no 404
        data = response.json()
        assert "detail" in data, "Login endpoint missing detail in error response"
        print("✅ Login endpoint exists")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_register_endpoint_exists():
    """
    Verifica que el endpoint de registro existe y responde.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(f"{BASE_URL}/api/v1/auth/register", json={})
        assert response.status_code == 422, f"Register endpoint unexpected status: {response.status_code}"
        print("✅ Register endpoint exists")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_jobs_endpoint_exists():
    """
    Verifica que el endpoint de jobs existe.
    Debe requerir autenticación.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}/api/v1/jobs")
        # Sin auth debe devolver 401 o 403
        assert response.status_code in [401, 403], \
            f"Jobs endpoint should require auth, got: {response.status_code}"
        print("✅ Jobs endpoint exists and requires auth")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_candidates_endpoint_exists():
    """
    Verifica que el endpoint de candidatos existe.
    Debe requerir autenticación.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}/api/v1/candidates")
        assert response.status_code in [401, 403], \
            f"Candidates endpoint should require auth, got: {response.status_code}"
        print("✅ Candidates endpoint exists and requires auth")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_matching_endpoint_exists():
    """
    Verifica que el endpoint de matching existe.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}/api/v1/matching")
        assert response.status_code in [200, 401, 403], \
            f"Matching endpoint unexpected status: {response.status_code}"
        print("✅ Matching endpoint exists")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_cors_headers():
    """
    Verifica que los headers CORS están configurados correctamente.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Hacer una petición OPTIONS (preflight)
        response = await client.options(
            f"{BASE_URL}/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Verificar headers CORS
        assert "access-control-allow-origin" in response.headers, \
            "Missing CORS header: access-control-allow-origin"
        assert "access-control-allow-methods" in response.headers, \
            "Missing CORS header: access-control-allow-methods"
        print("✅ CORS headers configured")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_security_headers():
    """
    Verifica que los headers de seguridad están presentes.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(BASE_URL)
        
        headers = response.headers
        assert "x-content-type-options" in headers, "Missing X-Content-Type-Options header"
        assert "x-frame-options" in headers, "Missing X-Frame-Options header"
        assert "strict-transport-security" in headers or os.getenv("DEBUG", "false").lower() == "true", \
            "Missing HSTS header (expected in production)"
        print("✅ Security headers present")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_ssl_redirect_in_production():
    """
    Verifica que en producción se fuerza HTTPS.
    Solo relevante si estamos en producción.
    """
    env = os.getenv("ENVIRONMENT", "development")
    if env != "production":
        pytest.skip("SSL redirect test only in production")
    
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
        try:
            response = await client.get(BASE_URL.replace("https://", "http://"))
            # Debe redirigir a HTTPS
            assert response.status_code in [301, 302, 307, 308], \
                "HTTP should redirect to HTTPS in production"
            assert "https" in response.headers.get("location", ""), \
                "Redirect should point to HTTPS"
            print("✅ SSL redirect configured")
        except Exception as e:
            pytest.fail(f"SSL redirect test failed: {str(e)}")


# Fixture para tests que requieren autenticación
@pytest.fixture(scope="module")
async def authenticated_client():
    """Crea un cliente HTTP autenticado para smoke tests."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Login con credenciales de test
        test_email = os.getenv("TEST_USER_EMAIL", "admin@example.com")
        test_password = os.getenv("TEST_USER_PASSWORD", "changeme")
        
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": test_email, "password": test_password}
        )
        
        if response.status_code == 200:
            # Extraer cookies
            cookies = response.cookies
            client.cookies.update(cookies)
            yield client
        else:
            pytest.skip("Could not authenticate - skipping authenticated tests")


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_login_functional(authenticated_client):
    """
    Verifica que el login funciona con credenciales válidas.
    Requiere TEST_USER_EMAIL y TEST_USER_PASSWORD configurados.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        test_email = os.getenv("TEST_USER_EMAIL")
        test_password = os.getenv("TEST_USER_PASSWORD")
        
        if not test_email or not test_password:
            pytest.skip("TEST_USER_EMAIL and TEST_USER_PASSWORD not configured")
        
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": test_email, "password": test_password}
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert data.get("success") is True, "Login response success != true"
        assert "user" in data, "Login response missing user object"
        assert response.cookies.get("access_token") is not None, "Missing access_token cookie"
        print("✅ Login functional test passed")


# Comando para ejecutar: pytest tests/smoke/ -v -m smoke
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "smoke"])
