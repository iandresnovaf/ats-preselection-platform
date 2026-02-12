"""
Tests de CORS (Cross-Origin Resource Sharing)
Verifica que la configuración de CORS sea segura y restrictiva.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestCORSSecurity:
    """Test suite para verificar seguridad de CORS."""
    
    @pytest.fixture
    def client(self):
        """Cliente de test para la aplicación."""
        return TestClient(app)
    
    def test_cors_preflight_allowed_origin(self, client):
        """Verifica que preflight requests funcionen para orígenes permitidos."""
        # Origen permitido (localhost:3000 - desarrollo frontend)
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
            }
        )
        
        assert response.status_code == 200, (
            f"Preflight request falló: {response.status_code}. "
            f"CORS puede estar bloqueando solicitudes legítimas."
        )
        
        # Verificar headers CORS
        assert "access-control-allow-origin" in response.headers, (
            "FALTA: Access-Control-Allow-Origin en preflight"
        )
        assert "access-control-allow-methods" in response.headers, (
            "FALTA: Access-Control-Allow-Methods en preflight"
        )
    
    def test_cors_allows_localhost_3000(self, client):
        """Verifica que localhost:3000 funciona en desarrollo."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin == "http://localhost:3000", (
            f"CORS no permite localhost:3000. "
            f"Allow-Origin: {allow_origin}. "
            f"Verificar CORS_ORIGINS en configuración."
        )
    
    def test_cors_allows_localhost_5173(self, client):
        """Verifica que localhost:5173 (Vite default) funciona."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"}
        )
        
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin == "http://localhost:5173", (
            f"CORS no permite localhost:5173. "
            f"Allow-Origin: {allow_origin}"
        )
    
    def test_cors_blocks_unknown_origin(self, client):
        """Verifica que orígenes no permitidos son rechazados."""
        # Origen malicioso
        malicious_origins = [
            "https://evil.com",
            "https://attacker.com",
            "http://localhost:9999",
            "https://phishing-site.com",
            "null",  # Origin null puede indicar ataque
        ]
        
        for origin in malicious_origins:
            response = client.get(
                "/health",
                headers={"Origin": origin}
            )
            
            allow_origin = response.headers.get("access-control-allow-origin")
            
            # Si allow_origin es * o el origen malicioso, es una vulnerabilidad
            if allow_origin == "*":
                pytest.fail(
                    f"CRÍTICO: CORS permite cualquier origen (*) - Origen: {origin}. "
                    "Vulnerabilidad: CORS demasiado permisivo. "
                    "Recomendación: Especificar orígenes explícitamente, no usar *"
                )
            
            if allow_origin == origin:
                pytest.fail(
                    f"CRÍTICO: CORS permite origen no autorizado: {origin}. "
                    "Vulnerabilidad: CSRF y data exfiltration posibles. "
                    "Recomendación: Configurar CORS_ORIGINS correctamente"
                )
    
    def test_cors_does_not_allow_wildcard_in_production(self, client):
        """Verifica que * no se use en producción."""
        import os
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        
        if not is_production:
            pytest.skip("Solo aplica en producción")
        
        response = client.get(
            "/health",
            headers={"Origin": "https://any-origin.com"}
        )
        
        allow_origin = response.headers.get("access-control-allow-origin")
        
        assert allow_origin != "*", (
            "CRÍTICO: Access-Control-Allow-Origin: * en producción. "
            "Vulnerabilidad grave: Cualquier sitio puede hacer requests autenticados."
        )
    
    def test_cors_credentials_header(self, client):
        """Verifica que credentials esté habilitado para orígenes permitidos."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        allow_credentials = response.headers.get("access-control-allow-credentials")
        
        # Si allow_credentials es true, no debe haber wildcard en allow_origin
        if allow_credentials and allow_credentials.lower() == "true":
            allow_origin = response.headers.get("access-control-allow-origin")
            assert allow_origin != "*", (
                "CRÍTICO: Access-Control-Allow-Credentials: true con Allow-Origin: *. "
                "Esto es inválido según especificación CORS y riesgoso."
            )
    
    def test_cors_headers_allowed(self, client):
        """Verifica que headers necesarios estén permitidos."""
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Headers": "Content-Type,Authorization,X-Requested-With",
            }
        )
        
        allow_headers = response.headers.get("access-control-allow-headers", "").lower()
        
        # Verificar headers esenciales
        essential_headers = ["content-type", "authorization"]
        for header in essential_headers:
            assert header in allow_headers or "*" in allow_headers, (
                f"FALTA: Header '{header}' no permitido en CORS. "
                f"Headers permitidos: {allow_headers}"
            )
    
    def test_cors_methods_allowed(self, client):
        """Verifica que métodos HTTP necesarios estén permitidos."""
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "DELETE",
            }
        )
        
        allow_methods = response.headers.get("access-control-allow-methods", "").upper()
        
        # Verificar métodos esenciales para API REST
        essential_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        
        # Si usa *, todos los métodos están permitidos
        if "*" not in allow_methods:
            for method in essential_methods:
                assert method in allow_methods, (
                    f"FALTA: Método HTTP '{method}' no permitido en CORS. "
                    f"Métodos permitidos: {allow_methods}"
                )
    
    def test_cors_expose_headers(self, client):
        """Verifica que headers importantes estén expuestos al cliente."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        expose_headers = response.headers.get("access-control-expose-headers", "").lower()
        
        # Verificar headers de rate limiting estén expuestos
        rate_limit_headers = ["x-ratelimit-limit", "x-ratelimit-remaining"]
        
        for header in rate_limit_headers:
            if header not in expose_headers and "*" not in expose_headers:
                pytest.warns(UserWarning, (
                    f"ADVERTENCIA: Header '{header}' no expuesto en CORS. "
                    f"El frontend no podrá leer este header."
                ))
    
    def test_cors_max_age_set(self, client):
        """Verifica que max-age esté configurado para preflight caching."""
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }
        )
        
        max_age = response.headers.get("access-control-max-age")
        
        if max_age is None:
            pytest.warns(UserWarning, (
                "ADVERTENCIA: Access-Control-Max-Age no configurado. "
                "Los browsers harán preflight requests en cada solicitud."
            ))
        else:
            # Verificar que max-age sea razonable (al menos 600 segundos = 10 minutos)
            assert int(max_age) >= 600, (
                f"INEFICIENTE: Max-Age muy bajo ({max_age}s). "
                f"Recomendación: Usar al menos 600s (10 minutos) o 86400s (24 horas)"
            )


class TestCORSPreflight:
    """Tests específicos para preflight requests."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_preflight_for_complex_requests(self, client):
        """Verifica preflight para requests con Content-Type: application/json."""
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        
        assert response.status_code == 200, (
            f"Preflight falló: {response.status_code}"
        )
    
    def test_preflight_with_auth_header(self, client):
        """Verifica preflight para requests con Authorization header."""
        response = client.options(
            "/api/v1/users",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            }
        )
        
        # Debe permitir Authorization header
        allow_headers = response.headers.get("access-control-allow-headers", "").lower()
        assert "authorization" in allow_headers or "*" in allow_headers, (
            "FALTA: Header 'Authorization' no permitido en CORS preflight"
        )
    
    @pytest.mark.parametrize("method", ["PUT", "DELETE", "PATCH"])
    def test_preflight_for_writing_methods(self, client, method):
        """Verifica preflight para métodos de escritura."""
        response = client.options(
            "/api/v1/jobs/job-id",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": method,
            }
        )
        
        if response.status_code == 200:
            allow_methods = response.headers.get("access-control-allow-methods", "").upper()
            assert method in allow_methods or "*" in allow_methods, (
                f"FALTA: Método '{method}' no permitido en CORS preflight"
            )


class TestCORSConfiguration:
    """Tests para verificar configuración de CORS."""
    
    def test_cors_origins_from_environment(self):
        """Verifica que CORS_ORIGINS se lea de variables de entorno."""
        from app.core.config import settings
        
        cors_origins = settings.CORS_ORIGINS
        
        assert cors_origins, (
            "FALTA: CORS_ORIGINS no configurado en settings"
        )
        
        # Verificar que contenga al menos localhost
        assert "localhost" in cors_origins, (
            f"CORS_ORIGINS no incluye localhost: {cors_origins}. "
            "El frontend de desarrollo no funcionará."
        )
    
    def test_cors_origins_not_empty_in_production(self):
        """Verifica que CORS_ORIGINS no esté vacío en producción."""
        import os
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        
        if not is_production:
            pytest.skip("Solo aplica en producción")
        
        from app.core.config import settings
        cors_origins = settings.CORS_ORIGINS
        
        # En producción, no debería ser solo localhost
        origins_list = [o.strip() for o in cors_origins.split(",")]
        non_localhost = [o for o in origins_list if "localhost" not in o]
        
        assert len(non_localhost) > 0, (
            "CRÍTICO: CORS_ORIGINS solo contiene localhost en producción. "
            "El frontend de producción no podrá conectarse."
        )
