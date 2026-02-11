"""
Tests for authentication endpoints and logic.
These are critical security tests.
"""
import pytest
from datetime import timedelta
from jose import jwt

from app.core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    authenticate_user,
    get_current_user,
)
from app.core.config import settings


pytestmark = pytest.mark.auth


# ============== Password Hashing Tests ==============

class TestPasswordHashing:
    """Tests for password hashing utilities."""
    
    def test_password_hashing(self, test_password):
        """Test that passwords are hashed correctly."""
        hashed = get_password_hash(test_password)
        assert hashed != test_password
        assert len(hashed) > 0
    
    def test_password_verification_success(self, test_password):
        """Test that correct password verifies successfully."""
        hashed = get_password_hash(test_password)
        assert verify_password(test_password, hashed) is True
    
    def test_password_verification_failure(self, test_password):
        """Test that incorrect password fails verification."""
        hashed = get_password_hash(test_password)
        assert verify_password("wrongpassword", hashed) is False
    
    def test_password_verification_different_passwords(self):
        """Test that different passwords produce different hashes."""
        password1 = "Password123!"
        password2 = "Password456!"
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        assert hash1 != hash2
    
    def test_password_verification_empty_password(self):
        """Test handling of empty password."""
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False


# ============== Token Creation Tests ==============

class TestTokenCreation:
    """Tests for JWT token creation."""
    
    def test_create_access_token(self, test_admin):
        """Test access token creation."""
        token = create_access_token(data={"sub": str(test_admin.id)})
        assert token is not None
        assert len(token.split('.')) == 3  # JWT has 3 parts
    
    def test_create_access_token_with_expiry(self, test_admin):
        """Test access token with custom expiry."""
        expires = timedelta(minutes=5)
        token = create_access_token(
            data={"sub": str(test_admin.id)},
            expires_delta=expires
        )
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(test_admin.id)
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self, test_admin):
        """Test refresh token creation."""
        token = create_refresh_token(data={"sub": str(test_admin.id)})
        assert token is not None
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(test_admin.id)
        assert payload["type"] == "refresh"
    
    def test_access_and_refresh_tokens_are_different(self, test_admin):
        """Test that access and refresh tokens differ."""
        access_token = create_access_token(data={"sub": str(test_admin.id)})
        refresh_token = create_refresh_token(data={"sub": str(test_admin.id)})
        assert access_token != refresh_token


# ============== Token Decoding Tests ==============

class TestTokenDecoding:
    """Tests for JWT token decoding."""
    
    def test_decode_valid_token(self, admin_token, test_admin):
        """Test decoding a valid token."""
        payload = decode_token(admin_token)
        assert payload is not None
        assert payload["sub"] == str(test_admin.id)
        assert payload["type"] == "access"
    
    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        payload = decode_token("invalid.token.here")
        assert payload is None
    
    def test_decode_expired_token(self, expired_token):
        """Test decoding an expired token."""
        payload = decode_token(expired_token)
        assert payload is None
    
    def test_decode_malformed_token(self):
        """Test decoding malformed tokens."""
        assert decode_token("") is None
        assert decode_token("not.a.token") is None
        assert decode_token("only.two.parts") is None


# ============== Authentication Tests ==============

@pytest.mark.asyncio
class TestAuthentication:
    """Tests for user authentication."""
    
    async def test_authenticate_user_success(self, db_session, test_admin, test_admin_data):
        """Test successful user authentication."""
        user = await authenticate_user(
            db_session,
            test_admin_data["email"],
            test_admin_data["password"]
        )
        assert user is not None
        assert user.email == test_admin_data["email"]
    
    async def test_authenticate_user_wrong_password(self, db_session, test_admin):
        """Test authentication with wrong password."""
        user = await authenticate_user(
            db_session,
            test_admin.email,
            "wrongpassword"
        )
        assert user is None
    
    async def test_authenticate_user_nonexistent(self, db_session):
        """Test authentication with non-existent user."""
        user = await authenticate_user(
            db_session,
            "nonexistent@test.com",
            "password123"
        )
        assert user is None
    
    async def test_authenticate_user_inactive(self, db_session, test_inactive_user, test_inactive_user_data):
        """Test authentication with inactive user."""
        # Note: authenticate_user doesn't check status, it just validates credentials
        user = await authenticate_user(
            db_session,
            test_inactive_user_data["email"],
            test_inactive_user_data["password"]
        )
        # Should authenticate but status check happens elsewhere
        assert user is not None
        assert user.status.value == "inactive"


# ============== Login Endpoint Tests ==============

@pytest.mark.asyncio
class TestLoginEndpoint:
    """Tests for /auth/login endpoint."""
    
    async def test_login_success(self, client, test_admin_data):
        """Test successful login."""
        response = await client.post("/api/v1/auth/login", json={
            "email": test_admin_data["email"],
            "password": test_admin_data["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
    
    async def test_login_invalid_credentials(self, client, test_admin):
        """Test login with invalid credentials."""
        response = await client.post("/api/v1/auth/login", json={
            "email": test_admin.email,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert "Credenciales incorrectas" in response.json()["detail"]
    
    async def test_login_inactive_user(self, client, test_inactive_user_data):
        """Test login with inactive user."""
        response = await client.post("/api/v1/auth/login", json={
            "email": test_inactive_user_data["email"],
            "password": test_inactive_user_data["password"]
        })
        assert response.status_code == 403
        assert "inactivo" in response.json()["detail"].lower()
    
    async def test_login_pending_user(self, client, test_pending_user_data):
        """Test login with pending user."""
        response = await client.post("/api/v1/auth/login", json={
            "email": test_pending_user_data["email"],
            "password": test_pending_user_data["password"]
        })
        assert response.status_code == 403
        assert "inactivo" in response.json()["detail"].lower()
    
    async def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "password123"
        })
        assert response.status_code == 401
    
    async def test_login_missing_email(self, client):
        """Test login without email."""
        response = await client.post("/api/v1/auth/login", json={
            "password": "password123"
        })
        assert response.status_code == 422
    
    async def test_login_missing_password(self, client):
        """Test login without password."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@test.com"
        })
        assert response.status_code == 422
    
    async def test_login_invalid_email_format(self, client):
        """Test login with invalid email format."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "password123"
        })
        assert response.status_code == 422


# ============== Refresh Token Tests ==============

@pytest.mark.asyncio
class TestRefreshToken:
    """Tests for /auth/refresh endpoint."""
    
    async def test_refresh_token_success(self, client, admin_refresh_token):
        """Test successful token refresh."""
        response = await client.post("/api/v1/auth/refresh", params={
            "refresh_token": admin_refresh_token
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    async def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token."""
        response = await client.post("/api/v1/auth/refresh", params={
            "refresh_token": "invalid.token.here"
        })
        assert response.status_code == 401
        assert "inválido" in response.json()["detail"].lower()
    
    async def test_refresh_token_with_access_token(self, client, admin_token):
        """Test refresh with access token (should fail)."""
        response = await client.post("/api/v1/auth/refresh", params={
            "refresh_token": admin_token
        })
        assert response.status_code == 401
    
    async def test_refresh_token_missing(self, client):
        """Test refresh without token."""
        response = await client.post("/api/v1/auth/refresh")
        assert response.status_code == 422


# ============== Logout Tests ==============

@pytest.mark.asyncio
class TestLogout:
    """Tests for /auth/logout endpoint."""
    
    async def test_logout_success(self, client, admin_refresh_token):
        """Test successful logout."""
        response = await client.post("/api/v1/auth/logout", params={
            "refresh_token": admin_refresh_token
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    async def test_logout_invalid_token(self, client):
        """Test logout with invalid token."""
        response = await client.post("/api/v1/auth/logout", params={
            "refresh_token": "invalid.token.here"
        })
        assert response.status_code == 401


# ============== Get Current User Tests ==============

@pytest.mark.asyncio
class TestGetCurrentUser:
    """Tests for /auth/me endpoint."""
    
    async def test_get_current_user_success(self, client, admin_headers, test_admin):
        """Test getting current user info."""
        response = await client.get("/api/v1/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_admin.email
        assert data["full_name"] == test_admin.full_name
        assert "id" in data
        assert "role" in data
    
    async def test_get_current_user_no_token(self, client):
        """Test getting current user without token."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 403
    
    async def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = await client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 401


# ============== Password Change Tests ==============

@pytest.mark.asyncio
class TestPasswordChange:
    """Tests for /auth/change-password endpoint."""
    
    async def test_change_password_success(self, client, admin_headers, test_admin_data):
        """Test successful password change."""
        response = await client.post("/api/v1/auth/change-password", 
            headers=admin_headers,
            json={
                "current_password": test_admin_data["password"],
                "new_password": "NewPassword123!"
            }
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    async def test_change_password_wrong_current(self, client, admin_headers):
        """Test password change with wrong current password."""
        response = await client.post("/api/v1/auth/change-password", 
            headers=admin_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "NewPassword123!"
            }
        )
        assert response.status_code == 400
        assert "incorrecto" in response.json()["detail"].lower()
    
    async def test_change_password_too_short(self, client, admin_headers, test_admin_data):
        """Test password change with short new password."""
        response = await client.post("/api/v1/auth/change-password", 
            headers=admin_headers,
            json={
                "current_password": test_admin_data["password"],
                "new_password": "short"
            }
        )
        assert response.status_code == 422
    
    async def test_change_password_unauthorized(self, client):
        """Test password change without authentication."""
        response = await client.post("/api/v1/auth/change-password", json={
            "current_password": "oldpass",
            "new_password": "NewPassword123!"
        })
        assert response.status_code == 403


# ============== Forgot/Reset Password Tests ==============

@pytest.mark.asyncio
class TestForgotResetPassword:
    """Tests for forgot and reset password endpoints."""
    
    async def test_forgot_password_existing_user(self, client, test_admin):
        """Test forgot password for existing user."""
        response = await client.post("/api/v1/auth/forgot-password", json={
            "email": test_admin.email
        })
        assert response.status_code == 200
        # Should not reveal if email exists
        assert response.json()["success"] is True
    
    async def test_forgot_password_nonexistent_user(self, client):
        """Test forgot password for non-existent user."""
        response = await client.post("/api/v1/auth/forgot-password", json={
            "email": "nonexistent@test.com"
        })
        assert response.status_code == 200
        # Should not reveal if email doesn't exist
        assert response.json()["success"] is True
    
    async def test_reset_password_invalid_token(self, client):
        """Test reset password with invalid token."""
        response = await client.post("/api/v1/auth/reset-password", json={
            "token": "invalid.token.here",
            "new_password": "NewPassword123!"
        })
        assert response.status_code == 400
        assert "inválido" in response.json()["detail"].lower()
    
    async def test_reset_password_short_password(self, client):
        """Test reset password with short password."""
        response = await client.post("/api/v1/auth/reset-password", json={
            "token": "some.token.here",
            "new_password": "short"
        })
        assert response.status_code == 422


# ============== Email Change Tests ==============

@pytest.mark.asyncio
class TestEmailChange:
    """Tests for /auth/change-email endpoint."""
    
    async def test_change_email_success(self, client, admin_headers, test_admin_data):
        """Test successful email change."""
        response = await client.post("/api/v1/auth/change-email", 
            headers=admin_headers,
            json={
                "new_email": "newemail@test.com",
                "password": test_admin_data["password"]
            }
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    async def test_change_email_wrong_password(self, client, admin_headers):
        """Test email change with wrong password."""
        response = await client.post("/api/v1/auth/change-email", 
            headers=admin_headers,
            json={
                "new_email": "newemail@test.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 400
    
    async def test_change_email_already_exists(self, client, admin_headers, test_consultant, test_admin_data):
        """Test email change to existing email."""
        response = await client.post("/api/v1/auth/change-email", 
            headers=admin_headers,
            json={
                "new_email": test_consultant.email,
                "password": test_admin_data["password"]
            }
        )
        assert response.status_code == 400
        assert "en uso" in response.json()["detail"].lower()


# ============== Role-Based Access Tests ==============

@pytest.mark.asyncio
class TestRoleBasedAccess:
    """Tests for role-based access control."""
    
    async def test_consultant_cannot_access_admin_endpoints(self, client, consultant_headers):
        """Test that consultants cannot access admin-only endpoints."""
        response = await client.get("/api/v1/users", headers=consultant_headers)
        assert response.status_code == 403
    
    async def test_admin_can_access_all_endpoints(self, client, admin_headers):
        """Test that admins can access user management endpoints."""
        response = await client.get("/api/v1/users", headers=admin_headers)
        assert response.status_code == 200
