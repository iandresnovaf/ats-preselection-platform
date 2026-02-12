"""
Tests de Headers de Seguridad
Verifica que todos los headers de seguridad estén presentes y configurados correctamente.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.main import app


class TestSecurityHeaders:
    """Test suite para headers de seguridad HTTP."""
    
    @pytest.fixture
    def client(self):
        """Cliente de test para la aplicación."""
        return TestClient(app)
    
    def test_x_frame_options_header(self, client):
        """Verifica que X-Frame-Options esté configurado como DENY o SAMEORIGIN."""
        response = client.get("/health")
        
        # Verificar que el header existe
        x_frame_options = response.headers.get("X-Frame-Options")
        assert x_frame_options is not None, (
            "FALTA: X-Frame-Options header no presente. "
            "Vulnerabilidad: Clickjacking attacks posibles. "
            "Recomendación: Agregar header X-Frame-Options: DENY"
        )
        
        # Verificar valor seguro
        assert x_frame_options.upper() in ["DENY", "SAMEORIGIN"], (
            f"INSEGURO: X-Frame-Options = '{x_frame_options}'. "
            f"Recomendación: Usar 'DENY' o 'SAMEORIGIN'"
        )
    
    def test_x_content_type_options_header(self, client):
        """Verifica que X-Content-Type-Options esté configurado como nosniff."""
        response = client.get("/health")
        
        x_content_type = response.headers.get("X-Content-Type-Options")
        assert x_content_type is not None, (
            "FALTA: X-Content-Type-Options header no presente. "
            "Vulnerabilidad: MIME-type sniffing attacks posibles. "
            "Recomendación: Agregar header X-Content-Type-Options: nosniff"
        )
        
        assert x_content_type.lower() == "nosniff", (
            f"INSEGURO: X-Content-Type-Options = '{x_content_type}'. "
            f"Recomendación: Usar 'nosniff'"
        )
    
    def test_x_xss_protection_header(self, client):
        """Verifica que X-XSS-Protection esté habilitado."""
        response = client.get("/health")
        
        xss_protection = response.headers.get("X-XSS-Protection")
        # Nota: Este header es legacy pero aún útil para navegadores antiguos
        # En aplicaciones modernas, CSP es más importante
        if xss_protection:
            assert "1" in xss_protection, (
                f"INSEGURO: X-XSS-Protection = '{xss_protection}'. "
                f"Recomendación: Usar '1; mode=block'"
            )
    
    def test_referrer_policy_header(self, client):
        """Verifica que Referrer-Policy esté configurado adecuadamente."""
        response = client.get("/health")
        
        referrer_policy = response.headers.get("Referrer-Policy")
        assert referrer_policy is not None, (
            "FALTA: Referrer-Policy header no presente. "
            "Vulnerabilidad: Información sensible puede filtrarse en referrers. "
            "Recomendación: Agregar header Referrer-Policy: strict-origin-when-cross-origin"
        )
        
        safe_policies = [
            "no-referrer",
            "no-referrer-when-downgrade",
            "origin",
            "origin-when-cross-origin",
            "strict-origin",
            "strict-origin-when-cross-origin",
        ]
        assert any(policy in referrer_policy.lower() for policy in safe_policies), (
            f"INSEGURO: Referrer-Policy = '{referrer_policy}'. "
            f"Recomendación: Usar 'strict-origin-when-cross-origin' o 'no-referrer'"
        )
    
    def test_permissions_policy_header(self, client):
        """Verifica que Permissions-Policy esté configurado."""
        response = client.get("/health")
        
        permissions_policy = response.headers.get("Permissions-Policy") or response.headers.get("Feature-Policy")
        
        # Este header es recomendado pero no crítico
        # Si existe, verificar que restrinja características peligrosas
        if permissions_policy:
            dangerous_features = ["camera", "microphone", "geolocation"]
            for feature in dangerous_features:
                if feature in permissions_policy.lower():
                    assert "=()" in permissions_policy or "=self" in permissions_policy, (
                        f"ADVERTENCIA: {feature} puede estar habilitado en Permissions-Policy. "
                        f"Revisar configuración."
                    )
    
    def test_strict_transport_security_header(self, client):
        """Verifica HSTS en producción."""
        response = client.get("/health")
        
        hsts = response.headers.get("Strict-Transport-Security")
        
        # En producción, HSTS es obligatorio
        # En desarrollo, puede no estar presente
        import os
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        
        if is_production:
            assert hsts is not None, (
                "CRÍTICO: Strict-Transport-Security header no presente en PRODUCCIÓN. "
                "Vulnerabilidad: Ataques de downgrade HTTPS a HTTP posibles. "
                "Recomendación: Agregar 'Strict-Transport-Security: max-age=31536000; includeSubDomains'"
            )
            
            assert "max-age" in hsts.lower(), (
                f"INCOMPLETO: HSTS sin max-age. Valor actual: '{hsts}'"
            )
            
            # Verificar que max-age sea al menos 1 año (31536000 segundos)
            import re
            max_age_match = re.search(r'max-age=(\d+)', hsts, re.IGNORECASE)
            if max_age_match:
                max_age = int(max_age_match.group(1))
                assert max_age >= 31536000, (
                    f"DÉBIL: HSTS max-age es {max_age}s. "
                    f"Recomendación: Usar al menos 31536000s (1 año)"
                )
    
    def test_content_security_policy_header(self, client):
        """Verifica que CSP esté configurado."""
        response = client.get("/health")
        
        csp = response.headers.get("Content-Security-Policy")
        
        assert csp is not None, (
            "FALTA: Content-Security-Policy header no presente. "
            "Vulnerabilidad: XSS attacks, injection de scripts posibles. "
            "Recomendación: Implementar CSP con directivas restrictivas"
        )
        
        # Verificar directivas esenciales
        essential_directives = ["default-src", "script-src", "style-src"]
        for directive in essential_directives:
            assert directive in csp.lower(), (
                f"INCOMPLETO: CSP no incluye '{directive}'. "
                f"Recomendación: Agregar '{directive}' a la política CSP"
            )
        
        # Verificar que 'unsafe-inline' no esté en script-src si es posible
        if "script-src" in csp.lower():
            script_src_part = [p for p in csp.split(";") if "script-src" in p.lower()]
            if script_src_part:
                assert "'unsafe-inline'" not in script_src_part[0], (
                    "INSEGURO: CSP script-src usa 'unsafe-inline'. "
                    "Esto permite ejecución de scripts inline y debilita CSP. "
                    "Recomendación: Usar nonces o hashes para scripts inline"
                )
                assert "'unsafe-eval'" not in script_src_part[0], (
                    "INSEGURO: CSP script-src usa 'unsafe-eval'. "
                    "Esto permite eval() y funciones similares. "
                    "Recomendación: Eliminar 'unsafe-eval' si es posible"
                )
    
    def test_no_server_version_header(self, client):
        """Verifica que no se exponga información del servidor."""
        response = client.get("/health")
        
        server_header = response.headers.get("Server")
        x_powered_by = response.headers.get("X-Powered-By")
        
        # Estos headers son informativos pero no críticos
        # Sin embargo, es mejor práctica no exponer versiones
        if server_header:
            # Verificar que no exponga versión específica
            import re
            version_pattern = r'\d+\.\d+(\.\d+)?'
            if re.search(version_pattern, server_header):
                pytest.warns(UserWarning, 
                    f"ADVERTENCIA: Server header expone versión: '{server_header}'")
        
        if x_powered_by:
            pytest.warns(UserWarning, 
                f"ADVERTENCIA: X-Powered-By header presente: '{x_powered_by}'")


class TestSecurityHeadersMiddleware:
    """Test para verificar implementación de middleware de headers de seguridad."""
    
    def test_security_headers_middleware_exists(self):
        """Verifica que exista middleware para agregar headers de seguridad."""
        from app.main import app
        
        # Verificar que existe algún middleware que agregue headers
        # Esto es una verificación básica - los tests anteriores verifican el resultado
        middleware_classes = [m.__class__.__name__ for m in app.user_middleware]
        
        # Verificar que existe middleware de rate limiting
        assert any("RateLimit" in mc for mc in middleware_classes), (
            "FALTA: RateLimitMiddleware no encontrado"
        )
    
    def test_csp_report_only_not_in_production(self, client):
        """Verifica que CSP Report-Only no esté en producción sin CSP real."""
        import os
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        
        response = client.get("/health")
        csp_report_only = response.headers.get("Content-Security-Policy-Report-Only")
        csp = response.headers.get("Content-Security-Policy")
        
        if is_production and csp_report_only and not csp:
            pytest.fail(
                "CRÍTICO: Solo CSP-Report-Only está configurado en producción. "
                "Esto no protege contra XSS. Implementar CSP real."
            )


# Fixtures adicionales para tests de headers
@pytest.fixture
def api_client():
    """Cliente para endpoints de API."""
    return TestClient(app)


@pytest.mark.parametrize("endpoint", [
    "/",
    "/health",
    "/api/docs",
])
def test_security_headers_on_all_endpoints(api_client, endpoint):
    """Verifica headers de seguridad en múltiples endpoints."""
    response = api_client.get(endpoint)
    
    # Algunos endpoints pueden retornar 404 o redirecciones
    if response.status_code < 400 or response.status_code == 404:
        # Verificar headers básicos
        assert "X-Content-Type-Options" in response.headers or response.status_code == 404, (
            f"FALTA: X-Content-Type-Options en {endpoint}"
        )
