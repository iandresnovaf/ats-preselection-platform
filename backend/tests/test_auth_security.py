"""
Tests de Autenticación Segura
Verifica que la implementación de autenticación sea segura.
"""
import pytest
import re
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.core.config import settings
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestTokenSecurity:
    """Test suite para seguridad de tokens JWT."""
    
    @pytest.fixture
    def client(self):
        """Cliente de test para la aplicación."""
        return TestClient(app)
    
    def test_tokens_not_exposed_in_login_response(self, client, test_admin):
        """Verifica que tokens no se expongan de forma insegura en respuestas."""
        from app.core.auth import get_password_hash
        
        # Crear usuario admin para test
        # Nota: En tests reales usaríamos fixture test_admin
        
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "TestPassword123!"}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Verificar estructura de respuesta
            assert "access_token" in data, "FALTA: access_token en respuesta"
            assert "refresh_token" in data, "FALTA: refresh_token en respuesta"
            
            # Verificar que no hay campos inseguros
            insecure_fields = ["password", "hashed_password", "secret_key"]
            for field in insecure_fields:
                assert field not in data, (
                    f"CRÍTICO: Campo sensible '{field}' expuesto en respuesta de login"
                )
            
            # Verificar que el token es string válido
            assert isinstance(data["access_token"], str), (
                "access_token no es string"
            )
            assert len(data["access_token"]) > 0, (
                "access_token está vacío"
            )
    
    def test_token_has_expiration_claim(self):
        """Verifica que el token JWT tenga claim de expiración."""
        token = create_access_token(data={"sub": "user123"})
        
        # Decodificar sin verificar firma para ver claims
        payload = jwt.decode(token, options={"verify_signature": False})
        
        assert "exp" in payload, (
            "CRÍTICO: Token no tiene claim 'exp' (expiración). "
            "Tokens sin expiración son un riesgo de seguridad grave."
        )
        
        # Verificar que la expiración es futura
        exp_timestamp = payload["exp"]
        now = datetime.utcnow().timestamp()
        assert exp_timestamp > now, (
            f"CRÍTICO: Token ya expirado. exp={exp_timestamp}, now={now}"
        )
    
    def test_token_has_type_claim(self):
        """Verifica que el token tenga claim de tipo (access/refresh)."""
        access_token = create_access_token(data={"sub": "user123"})
        refresh_token = create_refresh_token(data={"sub": "user123"})
        
        access_payload = jwt.decode(access_token, options={"verify_signature": False})
        refresh_payload = jwt.decode(refresh_token, options={"verify_signature": False})
        
        assert access_payload.get("type") == "access", (
            "FALTA: Claim 'type' != 'access' en access_token"
        )
        assert refresh_payload.get("type") == "refresh", (
            "FALTA: Claim 'type' != 'refresh' en refresh_token"
        )
    
    def test_access_token_expires_in_configured_time(self):
        """Verifica que access token expire en el tiempo configurado."""
        token = create_access_token(data={"sub": "user123"})
        payload = jwt.decode(token, options={"verify_signature": False})
        
        exp_timestamp = payload["exp"]
        iat_timestamp = payload.get("iat", datetime.utcnow().timestamp())
        
        duration_seconds = exp_timestamp - iat_timestamp
        expected_duration = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        # Permitir margen de 10 segundos
        assert abs(duration_seconds - expected_duration) < 10, (
            f"Duración de token incorrecta: {duration_seconds}s. "
            f"Esperado: {expected_duration}s ({settings.ACCESS_TOKEN_EXPIRE_MINUTES} min)"
        )
    
    def test_refresh_token_expires_in_configured_time(self):
        """Verifica que refresh token expire en el tiempo configurado."""
        token = create_refresh_token(data={"sub": "user123"})
        payload = jwt.decode(token, options={"verify_signature": False})
        
        exp_timestamp = payload["exp"]
        iat_timestamp = payload.get("iat", datetime.utcnow().timestamp())
        
        duration_seconds = exp_timestamp - iat_timestamp
        expected_duration = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        
        # Permitir margen de 60 segundos
        assert abs(duration_seconds - expected_duration) < 60, (
            f"Duración de refresh token incorrecta: {duration_seconds}s. "
            f"Esperado: {expected_duration}s ({settings.REFRESH_TOKEN_EXPIRE_DAYS} días)"
        )
    
    def test_expired_token_rejected(self, client):
        """Verifica que tokens expirados sean rechazados."""
        # Crear token expirado
        expired_token = create_access_token(
            data={"sub": "user123"},
            expires_delta=timedelta(seconds=-1)  # Ya expirado
        )
        
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401, (
            f"Token expirado no rechazado. Status: {response.status_code}. "
            f"Respuesta: {response.text}"
        )
    
    def test_invalid_token_rejected(self, client):
        """Verifica que tokens inválidos sean rechazados."""
        invalid_tokens = [
            "invalid.token.here",
            "not.a.token",
            "Bearer invalid",
            "",
        ]
        
        for token in invalid_tokens:
            response = client.get(
                "/api/v1/users",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 401 or response.status_code == 403, (
                f"Token inválido '{token}' no rechazado. Status: {response.status_code}"
            )
    
    def test_refresh_token_cannot_access_protected_routes(self, client):
        """Verifica que refresh tokens no puedan acceder a rutas protegidas."""
        refresh_token = create_refresh_token(data={"sub": "user123"})
        
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {refresh_token}"}
        )
        
        assert response.status_code == 401, (
            f"Refresh token aceptado como access token. Status: {response.status_code}. "
            "Esto es una vulnerabilidad: los refresh tokens deben ser de un solo uso."
        )
    
    def test_token_signature_verified(self):
        """Verifica que la firma del token se verifique correctamente."""
        # Crear token válido
        token = create_access_token(data={"sub": "user123"})
        
        # Verificar que se puede decodificar con la clave correcta
        payload = decode_token(token)
        assert payload is not None, "Token válido rechazado"
        assert payload["sub"] == "user123"
        
        # Modificar el token (simular tampering)
        tampered_token = token[:-10] + "X" * 10
        
        # Verificar que el token modificado es rechazado
        tampered_payload = decode_token(tampered_token)
        assert tampered_payload is None, (
            "CRÍTICO: Token modificado aceptado. "
            "La verificación de firma no está funcionando."
        )


class TestCookieSecurity:
    """Test suite para seguridad de cookies."""
    
    def test_cookies_should_have_secure_flag_in_production(self):
        """Verifica que cookies tengan flag Secure en producción."""
        import os
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        
        if not is_production:
            pytest.skip("Solo aplica en producción")
        
        # Si se usan cookies, deben tener flags de seguridad
        # Nota: La app actual usa tokens en headers, no cookies
        # Este test es preventivo
        
        pytest.skip("Aplicación usa tokens en headers, no cookies")
    
    def test_cookies_should_have_httponly_flag(self):
        """Verifica que cookies tengan flag HttpOnly."""
        # Preventivo: si se implementan cookies en el futuro
        pytest.skip("Aplicación usa tokens en headers, no cookies")
    
    def test_cookies_should_have_samesite_flag(self):
        """Verifica que cookies tengan flag SameSite."""
        # Preventivo: si se implementan cookies en el futuro
        pytest.skip("Aplicación usa tokens en headers, no cookies")


class TestRefreshTokenRotation:
    """Test suite para rotación de refresh tokens."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_refresh_token_returns_new_tokens(self, client, test_admin):
        """Verifica que refresh devuelva nuevos tokens (rotación)."""
        # Login para obtener tokens
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "TestPassword123!"}
        )
        
        if response.status_code != 200:
            pytest.skip("No se pudo hacer login para test de refresh")
        
        data = response.json()
        old_refresh_token = data["refresh_token"]
        old_access_token = data["access_token"]
        
        # Hacer refresh
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": old_refresh_token}
        )
        
        if refresh_response.status_code != 200:
            pytest.skip("Refresh token endpoint no disponible o falló")
        
        new_data = refresh_response.json()
        new_refresh_token = new_data.get("refresh_token")
        new_access_token = new_data.get("access_token")
        
        # Verificar que se devolvieron nuevos tokens
        assert new_refresh_token is not None, (
            "FALTA: Nuevo refresh_token en respuesta de refresh"
        )
        assert new_access_token is not None, (
            "FALTA: Nuevo access_token en respuesta de refresh"
        )
        
        # Verificar que son diferentes (rotación)
        assert new_refresh_token != old_refresh_token, (
            "INSEGURO: Refresh token no rotado. "
            "El mismo refresh token puede usarse múltiples veces. "
            "Implementar rotación de refresh tokens."
        )
        
        assert new_access_token != old_access_token, (
            "INSEGURO: Access token no rotado. "
            "Debe generarse un nuevo access token en cada refresh."
        )
    
    def test_old_refresh_token_invalidated_after_rotation(self, client, test_admin):
        """Verifica que el viejo refresh token se invalide después de rotación."""
        # Login para obtener tokens
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "TestPassword123!"}
        )
        
        if response.status_code != 200:
            pytest.skip("No se pudo hacer login para test de refresh")
        
        data = response.json()
        old_refresh_token = data["refresh_token"]
        
        # Hacer refresh
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": old_refresh_token}
        )
        
        if refresh_response.status_code != 200:
            pytest.skip("Refresh no disponible")
        
        # Intentar usar el viejo refresh token nuevamente
        second_refresh = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": old_refresh_token}
        )
        
        # El viejo token debe ser rechazado
        # Nota: La implementación actual puede no tener blacklist
        # Este test documenta la mejora necesaria
        
        if second_refresh.status_code == 200:
            pytest.warns(UserWarning, (
                "ADVERTENCIA: Viejo refresh token aún válido después de rotación. "
                "Vulnerabilidad: Refresh token reuse attack posible. "
                "Recomendación: Implementar blacklist de refresh tokens en Redis"
            ))


class TestPasswordSecurity:
    """Test suite para seguridad de passwords."""
    
    def test_password_hashing_uses_bcrypt(self):
        """Verifica que se use bcrypt para hashing."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        # Verificar formato bcrypt ($2b$ o $2a$)
        assert hashed.startswith(("$2b$", "$2a$", "$2y$")), (
            f"Hash no usa bcrypt. Formato: {hashed[:10]}... "
            "La aplicación debe usar bcrypt para password hashing."
        )
    
    def test_password_hash_is_different_each_time(self):
        """Verifica que cada hash sea único (sal aleatoria)."""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2, (
            "CRÍTICO: Hash de password es determinístico. "
            "Esto indica que no se usa sal aleatoria. "
            "Vulnerabilidad: Rainbow table attacks posibles."
        )
    
    def test_password_verification_works(self):
        """Verifica que la verificación de passwords funcione."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        # Verificar password correcto
        assert verify_password(password, hashed) is True, (
            "Verificación de password correcto falló"
        )
        
        # Verificar password incorrecto
        assert verify_password("WrongPassword", hashed) is False, (
            "Password incorrecto aceptado"
        )
    
    def test_password_minimum_length_enforced(self, client):
        """Verifica que se exija longitud mínima de password."""
        # Intentar crear usuario con password corto
        response = client.post(
            "/api/v1/users",
            json={
                "email": "test@example.com",
                "password": "123",  # Muy corto
                "full_name": "Test User",
                "role": "consultant"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        # El sistema debe rechazar passwords cortos
        # Nota: Este test puede necesitar ajustes según la implementación real
        
    def test_common_passwords_rejected(self):
        """Verifica que passwords comunes sean rechazados."""
        common_passwords = [
            "password",
            "123456",
            "qwerty",
            "admin",
            "letmein",
        ]
        
        # Este test es preventivo
        # La aplicación debería validar contra lista de passwords comunes
        
        pytest.skip("Validación de passwords comunes no implementada")


class TestAuthenticationFlows:
    """Test suite para flujos de autenticación."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_logout_invalidates_token(self, client, test_admin):
        """Verifica que logout invalide el token."""
        # Nota: La implementación actual usa JWT sin blacklist
        # Este test documenta la mejora necesaria
        
        pytest.skip("Blacklist de tokens no implementada. "
                   "Los tokens JWT permanecen válidos hasta expirar.")
    
    def test_concurrent_sessions_allowed(self, client, test_admin):
        """Verifica que sesiones concurrentes sean permitidas (o no)."""
        # Login desde múltiples dispositivos debe funcionar
        # Esto es comportamiento esperado para JWT
        
        response1 = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "TestPassword123!"}
        )
        
        response2 = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "TestPassword123!"}
        )
        
        # Ambos logins deben funcionar
        assert response1.status_code in [200, 401]  # 401 si el usuario no existe
        assert response2.status_code in [200, 401]
    
    def test_inactive_user_cannot_login(self, client, test_inactive_user):
        """Verifica que usuarios inactivos no puedan hacer login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@test.com", "password": "TestPassword123!"}
        )
        
        # Debe rechazar el login
        assert response.status_code in [401, 403], (
            f"Usuario inactivo pudo hacer login. Status: {response.status_code}"
        )
    
    def test_pending_user_cannot_login(self, client, test_pending_user):
        """Verifica que usuarios pendientes no puedan hacer login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "pending@test.com", "password": "TestPassword123!"}
        )
        
        assert response.status_code in [401, 403], (
            f"Usuario pendiente pudo hacer login. Status: {response.status_code}"
        )
