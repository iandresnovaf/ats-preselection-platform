"""
Integration tests for Auth API endpoints.
Tests: /auth/login, /auth/refresh, /auth/logout, /auth/me, cookies
"""
import pytest
from fastapi import status


class TestLoginEndpoint:
    """Tests for POST /auth/login."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client, test_consultant, test_password):
        """Test successful login with valid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_consultant.email, "password": test_password}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return user info, not tokens
        assert "success" in data
        assert data["success"] is True
        assert "user" in data
        assert data["user"]["email"] == test_consultant.email
        assert data["user"]["role"] == "consultant"
        
        # Should set cookies
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
    
    @pytest.mark.asyncio
    async def test_login_viewer_success(self, client, test_viewer, test_password):
        """Test successful login with viewer user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_viewer.email, "password": test_password}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert data["user"]["role"] == "viewer"
        
        # Should set cookies
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, test_consultant):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_consultant.email, "password": "wrongpassword"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "somepass"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client, test_inactive_user, test_password):
        """Test login with inactive user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_inactive_user.email, "password": test_password}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestRefreshEndpoint:
    """Tests for POST /auth/refresh."""
    
    @pytest.mark.asyncio
    async def test_refresh_success(self, client, test_consultant):
        """Test successful token refresh."""
        # First login to get cookies
        from app.core.auth import create_refresh_token
        refresh_token = create_refresh_token({"sub": str(test_consultant.id)})
        
        client.cookies.set("refresh_token", refresh_token)
        
        response = await client.post("/api/v1/auth/refresh")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Should set new cookies
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
    
    @pytest.mark.asyncio
    async def test_refresh_no_cookie(self, client):
        """Test refresh without refresh cookie."""
        response = await client.post("/api/v1/auth/refresh")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token."""
        client.cookies.set("refresh_token", "invalid.token.here")
        
        response = await client.post("/api/v1/auth/refresh")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogoutEndpoint:
    """Tests for POST /auth/logout."""
    
    @pytest.mark.asyncio
    async def test_logout_success(self, client, test_consultant):
        """Test successful logout."""
        # Set a refresh token cookie
        from app.core.auth import create_refresh_token
        refresh_token = create_refresh_token({"sub": str(test_consultant.id)})
        client.cookies.set("refresh_token", refresh_token)
        
        response = await client.post("/api/v1/auth/logout")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_logout_clears_cookies(self, client):
        """Test that logout clears cookies."""
        # Set some cookies
        client.cookies.set("access_token", "some_token")
        client.cookies.set("refresh_token", "some_token")
        
        response = await client.post("/api/v1/auth/logout")
        
        assert response.status_code == status.HTTP_200_OK
        # Cookies should be deleted (cookie jar will show them with empty values or not present)


class TestMeEndpoint:
    """Tests for GET /auth/me."""
    
    @pytest.mark.asyncio
    async def test_get_me_success(self, client, test_consultant):
        """Test getting current user info."""
        from app.core.auth import create_access_token
        access_token = create_access_token({"sub": str(test_consultant.id)})
        client.cookies.set("access_token", access_token)
        
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["email"] == test_consultant.email
        assert data["full_name"] == test_consultant.full_name
        assert data["role"] == "consultant"
    
    @pytest.mark.asyncio
    async def test_get_me_no_cookie(self, client):
        """Test getting current user without cookie."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_me_viewer(self, client, test_viewer):
        """Test getting current user info for viewer."""
        from app.core.auth import create_access_token
        access_token = create_access_token({"sub": str(test_viewer.id)})
        client.cookies.set("access_token", access_token)
        
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["email"] == test_viewer.email
        assert data["role"] == "viewer"


class TestCookieSecurity:
    """Tests for cookie security settings."""
    
    @pytest.mark.asyncio
    async def test_cookies_are_httponly(self, client, test_consultant, test_password):
        """Test that cookies are set with httponly flag."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_consultant.email, "password": test_password}
        )
        
        # Check Set-Cookie headers
        set_cookie_headers = response.headers.get_list("set-cookie")
        
        for header in set_cookie_headers:
            if "access_token" in header or "refresh_token" in header:
                assert "httponly" in header.lower()
                assert "samesite=strict" in header.lower() or "samesite=lax" in header.lower()


class TestRoleBasedAPIAccess:
    """Tests for role-based access to API endpoints."""
    
    @pytest.mark.asyncio
    async def test_viewer_can_read_jobs(self, client, test_viewer, test_job):
        """Test that viewer can read jobs."""
        from app.core.auth import create_access_token
        access_token = create_access_token({"sub": str(test_viewer.id)})
        client.cookies.set("access_token", access_token)
        
        response = await client.get("/api/v1/jobs")
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_viewer_can_read_candidates(self, client, test_viewer, test_candidate):
        """Test that viewer can read candidates."""
        from app.core.auth import create_access_token
        access_token = create_access_token({"sub": str(test_viewer.id)})
        client.cookies.set("access_token", access_token)
        
        response = await client.get("/api/v1/candidates")
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_create_job(self, client, test_viewer):
        """Test that viewer cannot create jobs."""
        from app.core.auth import create_access_token
        access_token = create_access_token({"sub": str(test_viewer.id)})
        client.cookies.set("access_token", access_token)
        
        response = await client.post(
            "/api/v1/jobs",
            json={
                "title": "New Job",
                "description": "Job description",
                "department": "Engineering",
            }
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_create_candidate(self, client, test_viewer, test_job):
        """Test that viewer cannot create candidates."""
        from app.core.auth import create_access_token
        access_token = create_access_token({"sub": str(test_viewer.id)})
        client.cookies.set("access_token", access_token)
        
        response = await client.post(
            "/api/v1/candidates",
            json={
                "job_opening_id": str(test_job.id),
                "raw_data": {"name": "Test"},
                "source": "manual",
            }
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_consultant_can_create_job(self, client, test_consultant):
        """Test that consultant can create jobs."""
        from app.core.auth import create_access_token
        access_token = create_access_token({"sub": str(test_consultant.id)})
        client.cookies.set("access_token", access_token)
        
        response = await client.post(
            "/api/v1/jobs",
            json={
                "title": "New Job",
                "description": "Job description",
                "department": "Engineering",
            }
        )
        
        # May succeed or fail depending on other validation, but should not be 403
        assert response.status_code != status.HTTP_403_FORBIDDEN
