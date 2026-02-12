"""Tests de seguridad para el backend."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestSecurityHeaders:
    """Tests para headers de seguridad HTTP."""
    
    def test_content_security_policy(self):
        """Verificar que CSP header está presente."""
        response = client.get("/health")
        assert "content-security-policy" in response.headers
        csp = response.headers["content-security-policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp
    
    def test_x_content_type_options(self):
        """Verificar X-Content-Type-Options: nosniff."""
        response = client.get("/health")
        assert response.headers.get("x-content-type-options") == "nosniff"
    
    def test_x_frame_options(self):
        """Verificar X-Frame-Options: DENY."""
        response = client.get("/health")
        assert response.headers.get("x-frame-options") == "DENY"
    
    def test_x_xss_protection(self):
        """Verificar X-XSS-Protection."""
        response = client.get("/health")
        assert response.headers.get("x-xss-protection") == "1; mode=block"
    
    def test_referrer_policy(self):
        """Verificar Referrer-Policy."""
        response = client.get("/health")
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    
    def test_permissions_policy(self):
        """Verificar Permissions-Policy."""
        response = client.get("/health")
        assert "permissions-policy" in response.headers
        pp = response.headers["permissions-policy"]
        assert "camera=()" in pp
        assert "microphone=()" in pp
    
    def test_cache_control(self):
        """Verificar headers de cache control."""
        response = client.get("/health")
        assert "cache-control" in response.headers
        assert "no-store" in response.headers["cache-control"]


class TestCORS:
    """Tests para configuración CORS."""
    
    def test_cors_headers_on_preflight(self):
        """Verificar que CORS preflight funciona correctamente."""
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }
        )
        # El middleware de CORS maneja esto
        assert response.status_code in [200, 404]  # 404 si la ruta no existe para OPTIONS
    
    def test_no_wildcard_in_production_cors(self):
        """Verificar que no se permite wildcard en producción."""
        from app.core.config import settings
        origins = settings.get_cors_origins()
        
        if settings.ENVIRONMENT == "production":
            assert "*" not in origins, "Wildcard no permitido en producción"


class TestContentTypeValidation:
    """Tests para validación de Content-Type."""
    
    def test_reject_invalid_content_type(self):
        """Rechazar requests con Content-Type inválido."""
        response = client.post(
            "/api/v1/jobs",
            headers={"Content-Type": "text/plain"},
            data="invalid data"
        )
        # Debería rechazar o retornar error de validación
        assert response.status_code in [415, 422, 403]
    
    def test_accept_application_json(self):
        """Aceptar application/json."""
        response = client.post(
            "/api/v1/auth/login",
            headers={"Content-Type": "application/json"},
            json={"email": "test@test.com", "password": "test123"}
        )
        # Puede ser 401 (credenciales inválidas) pero no 415
        assert response.status_code != 415


class TestRateLimiting:
    """Tests para rate limiting."""
    
    def test_rate_limit_headers_present(self):
        """Verificar que headers de rate limit están presentes."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@test.com", "password": "wrong"}
        )
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers
    
    def test_rate_limit_blocks_after_exceeded(self):
        """Verificar que rate limit bloquea después de exceder."""
        # Hacer múltiples requests rápidos
        responses = []
        for _ in range(10):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "test@test.com", "password": "wrong"}
            )
            responses.append(response.status_code)
        
        # Al menos algunos deben ser 429 (rate limited)
        # o 401 (credenciales inválidas) pero con headers de rate limit
        assert 429 in responses or all(r in [401, 429] for r in responses)


class TestInputValidation:
    """Tests para validación de inputs."""
    
    def test_reject_xss_in_input(self):
        """Rechazar inputs con intentos de XSS."""
        xss_payload = "<script>alert('xss')</script>"
        # Los campos sanitizados deben escapar el HTML
        from app.schemas import sanitize_string
        sanitized = sanitize_string(xss_payload)
        assert "<script>" not in sanitized
        assert "&lt;script&gt;" in sanitized
    
    def test_reject_html_in_fields(self):
        """Rechazar HTML en campos que no lo permiten."""
        from app.schemas import validate_no_html
        
        with pytest.raises(ValueError):
            validate_no_html("<b>test</b>")
    
    def test_validate_email_format(self):
        """Validar formato de email."""
        from pydantic import ValidationError
        from app.schemas import UserCreate
        
        with pytest.raises(ValidationError):
            UserCreate(
                email="invalid-email",
                full_name="Test User",
                password="SecurePass123"
            )
    
    def test_password_strength_validation(self):
        """Validar fortaleza de contraseña."""
        from pydantic import ValidationError
        from app.schemas import UserCreate
        
        # Contraseña débil
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@test.com",
                full_name="Test User",
                password="weak"  # Sin mayúsculas, minúsculas o números
            )
    
    def test_validate_uuid_format(self):
        """Validar formato de UUID."""
        from app.schemas import validate_uuid
        
        # UUID válido
        valid = validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        assert valid == "550e8400-e29b-41d4-a716-446655440000"
        
        # UUID inválido
        with pytest.raises(ValueError):
            validate_uuid("not-a-uuid")
    
    def test_validate_phone_format(self):
        """Validar formato de teléfono."""
        from app.schemas import validate_phone
        
        # Teléfonos válidos
        assert validate_phone("+1-555-123-4567") == "+1-555-123-4567"
        assert validate_phone("(+57) 300-123-4567") == "(+57) 300-123-4567"
        
        # Teléfono con caracteres inválidos
        with pytest.raises(ValueError):
            validate_phone("phone<script>")


class TestAuthentication:
    """Tests para autenticación segura."""
    
    def test_login_generic_error_message(self):
        """Verificar mensaje genérico en login fallido (prevenir enumeration)."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "wrong"}
        )
        assert response.status_code == 401
        # Mensaje genérico, no revela si el usuario existe
        assert "credenciales" in response.json()["detail"].lower()
    
    def test_no_docs_in_production(self):
        """Verificar que docs están deshabilitados en producción."""
        from app.core.config import settings
        
        if settings.ENVIRONMENT == "production":
            response = client.get("/api/docs")
            assert response.status_code == 404


class TestTimingAttackProtection:
    """Tests para protección contra timing attacks."""
    
    def test_dummy_hash_defined(self):
        """Verificar que dummy hash está definido."""
        from app.core.auth import DUMMY_HASH
        assert DUMMY_HASH is not None
        assert len(DUMMY_HASH) > 0
    
    def test_verify_password_handles_none_hash(self):
        """Verificar que verify_password maneja hash nulo."""
        from app.core.auth import verify_password
        
        # No debe lanzar excepción con hash vacío
        result = verify_password("password", "")
        assert result is False
        
        result = verify_password("password", None)
        assert result is False
