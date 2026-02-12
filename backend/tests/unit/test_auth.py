"""
Unit tests for authentication and authorization.
Tests: login, refresh, logout, cookies, role-based access control.
"""
import pytest
from datetime import timedelta
from fastapi import HTTPException, status

from app.core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    authenticate_user,
    get_current_user_from_cookie,
)
from app.core.deps import require_admin, require_consultant, require_viewer
from app.models import UserRole, UserStatus


# ============== Password Hashing Tests ==============

class TestPasswordHashing:
    """Tests for password hashing functions."""
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed and verified."""
        password = "SecurePass123!"
        hashed = get_password_hash(password)
        
        # Verify hash is different from plain text
        assert hashed != password
        assert hashed.startswith("$2")  # bcrypt hash prefix
    
    def test_password_verification_success(self):
        """Test successful password verification."""
        password = "SecurePass123!"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_verification_failure(self):
        """Test failed password verification."""
        password = "SecurePass123!"
        wrong_password = "WrongPass123!"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_password_timing_protection(self):
        """Test that timing attack protection works."""
        # Even with empty hash, verification should not error
        assert verify_password("some_password", "") is False


# ============== JWT Token Tests ==============

class TestJWTokens:
    """Tests for JWT token creation and validation."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user-123"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user-123"}
        token = create_refresh_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"
        assert "exp" in payload
    
    def test_token_expiration(self):
        """Test that tokens have expiration."""
        data = {"sub": "user-123"}
        
        # Access token
        access_token = create_access_token(data, expires_delta=timedelta(minutes=15))
        access_payload = decode_token(access_token)
        assert access_payload["exp"] is not None
        
        # Refresh token
        refresh_token = create_refresh_token(data)
        refresh_payload = decode_token(refresh_token)
        assert refresh_payload["exp"] is not None
    
    def test_decode_invalid_token(self):
        """Test decoding of invalid token."""
        assert decode_token("invalid.token") is None
        assert decode_token("not.a.token") is None
        assert decode_token("") is None


# ============== Authentication Tests ==============

class TestAuthentication:
    """Tests for user authentication."""
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, db_session, test_consultant, test_password):
        """Test successful user authentication."""
        user = await authenticate_user(
            db_session, 
            test_consultant.email, 
            test_password
        )
        
        assert user is not None
        assert user.email == test_consultant.email
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, db_session, test_consultant):
        """Test authentication with wrong password."""
        user = await authenticate_user(
            db_session,
            test_consultant.email,
            "wrong_password"
        )
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent(self, db_session):
        """Test authentication for non-existent user."""
        user = await authenticate_user(
            db_session,
            "nonexistent@test.com",
            "some_password"
        )
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, db_session, test_inactive_user, test_password):
        """Test authentication for inactive user."""
        user = await authenticate_user(
            db_session,
            test_inactive_user.email,
            test_password
        )
        
        assert user is None


# ============== Role-Based Access Control Tests ==============

class TestRoleBasedAccess:
    """Tests for role-based access control."""
    
    @pytest.mark.asyncio
    async def test_require_admin_with_admin(self, test_admin):
        """Test require_admin with admin user."""
        user = await require_admin(test_admin)
        assert user == test_admin
    
    @pytest.mark.asyncio
    async def test_require_admin_with_consultant(self, test_consultant):
        """Test require_admin with consultant user - should fail."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(test_consultant)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_require_admin_with_viewer(self, test_viewer):
        """Test require_admin with viewer user - should fail."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(test_viewer)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_require_consultant_with_admin(self, test_admin):
        """Test require_consultant with admin user."""
        user = await require_consultant(test_admin)
        assert user == test_admin
    
    @pytest.mark.asyncio
    async def test_require_consultant_with_consultant(self, test_consultant):
        """Test require_consultant with consultant user."""
        user = await require_consultant(test_consultant)
        assert user == test_consultant
    
    @pytest.mark.asyncio
    async def test_require_consultant_with_viewer(self, test_viewer):
        """Test require_consultant with viewer user - should fail."""
        with pytest.raises(HTTPException) as exc_info:
            await require_consultant(test_viewer)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_require_viewer_with_admin(self, test_admin):
        """Test require_viewer with admin user."""
        user = await require_viewer(test_admin)
        assert user == test_admin
    
    @pytest.mark.asyncio
    async def test_require_viewer_with_consultant(self, test_consultant):
        """Test require_viewer with consultant user."""
        user = await require_viewer(test_consultant)
        assert user == test_consultant
    
    @pytest.mark.asyncio
    async def test_require_viewer_with_viewer(self, test_viewer):
        """Test require_viewer with viewer user."""
        user = await require_viewer(test_viewer)
        assert user == test_viewer


# ============== Cookie Authentication Tests ==============

class TestCookieAuthentication:
    """Tests for cookie-based authentication."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_from_cookie_success(self, db_session, test_admin):
        """Test getting user from valid cookie."""
        # Create a mock request with cookie
        class MockRequest:
            def __init__(self):
                self.cookies = {"access_token": create_access_token({"sub": str(test_admin.id)})}
        
        request = MockRequest()
        user = await get_current_user_from_cookie(request, db_session)
        
        assert user is not None
        assert user.id == test_admin.id
    
    @pytest.mark.asyncio
    async def test_get_current_user_from_cookie_no_token(self, db_session):
        """Test getting user from request without cookie."""
        class MockRequest:
            def __init__(self):
                self.cookies = {}
        
        request = MockRequest()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_cookie(request, db_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_current_user_from_cookie_invalid_token(self, db_session):
        """Test getting user with invalid token in cookie."""
        class MockRequest:
            def __init__(self):
                self.cookies = {"access_token": "invalid.token.here"}
        
        request = MockRequest()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_cookie(request, db_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# ============== Integration with Cookie Settings ==============

class TestCookieSettings:
    """Tests for cookie security settings."""
    
    def test_cookie_settings_structure(self):
        """Test that cookie settings have required attributes."""
        from app.api.auth import COOKIE_SETTINGS
        
        assert "httponly" in COOKIE_SETTINGS
        assert "secure" in COOKIE_SETTINGS
        assert "samesite" in COOKIE_SETTINGS
        assert "path" in COOKIE_SETTINGS
        
        assert COOKIE_SETTINGS["httponly"] is True
        assert COOKIE_SETTINGS["samesite"] == "strict"
        assert COOKIE_SETTINGS["path"] == "/"
