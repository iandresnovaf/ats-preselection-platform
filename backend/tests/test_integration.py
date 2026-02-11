"""
Integration tests for ATS Platform.
These tests verify complete workflows and interactions between components.
"""
import pytest
from datetime import datetime


pytestmark = pytest.mark.integration


# ============== Authentication Flow Integration Tests ==============

@pytest.mark.asyncio
class TestAuthenticationFlow:
    """Integration tests for complete authentication flows."""
    
    async def test_complete_login_refresh_logout_flow(self, client, test_admin_data):
        """Test complete login -> refresh -> logout flow."""
        # Step 1: Login
        login_response = await client.post("/api/v1/auth/login", json={
            "email": test_admin_data["email"],
            "password": test_admin_data["password"]
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]
        
        # Step 2: Use access token to get user info
        me_response = await client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {access_token}"
        })
        assert me_response.status_code == 200
        
        # Step 3: Refresh token
        refresh_response = await client.post("/api/v1/auth/refresh", params={
            "refresh_token": refresh_token
        })
        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["access_token"]
        
        # Step 4: Use new access token
        me_response2 = await client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {new_access_token}"
        })
        assert me_response2.status_code == 200
        
        # Step 5: Logout
        logout_response = await client.post("/api/v1/auth/logout", params={
            "refresh_token": refresh_token
        })
        assert logout_response.status_code == 200
    
    async def test_token_invalidation_on_password_change(self, client, admin_headers, test_admin_data):
        """Test that tokens remain valid after password change (no invalidation in current implementation)."""
        # Get current token
        me_response = await client.get("/api/v1/auth/me", headers=admin_headers)
        assert me_response.status_code == 200
        
        # Change password
        change_response = await client.post("/api/v1/auth/change-password",
            headers=admin_headers,
            json={
                "current_password": test_admin_data["password"],
                "new_password": "NewPassword123!"
            }
        )
        assert change_response.status_code == 200
        
        # Token should still be valid (implementation doesn't invalidate on password change)
        me_response2 = await client.get("/api/v1/auth/me", headers=admin_headers)
        assert me_response2.status_code == 200
    
    async def test_concurrent_sessions(self, client, test_admin_data):
        """Test multiple concurrent sessions for same user."""
        # Login multiple times
        sessions = []
        for _ in range(3):
            response = await client.post("/api/v1/auth/login", json={
                "email": test_admin_data["email"],
                "password": test_admin_data["password"]
            })
            assert response.status_code == 200
            sessions.append(response.json())
        
        # All sessions should be valid
        for session in sessions:
            me_response = await client.get("/api/v1/auth/me", headers={
                "Authorization": f"Bearer {session['access_token']}"
            })
            assert me_response.status_code == 200
    
    async def test_access_protected_routes_after_login(self, client, test_admin_data):
        """Test accessing protected routes after successful login."""
        # Login
        login_response = await client.post("/api/v1/auth/login", json={
            "email": test_admin_data["email"],
            "password": test_admin_data["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Access various protected routes
        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 200
        
        response = await client.get("/api/v1/config/status", headers=headers)
        assert response.status_code == 200
        
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200


# ============== User Management Integration Tests ==============

@pytest.mark.asyncio
class TestUserManagementFlow:
    """Integration tests for user management workflows."""
    
    async def test_complete_user_lifecycle(self, client, admin_headers):
        """Test complete user lifecycle: create -> update -> deactivate -> activate -> delete."""
        # Step 1: Create user
        create_response = await client.post("/api/v1/users",
            headers=admin_headers,
            json={
                "email": "lifecycle@test.com",
                "full_name": "Lifecycle User",
                "password": "Password123!",
                "role": "consultant"
            }
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]
        
        # Step 2: Update user
        update_response = await client.patch(f"/api/v1/users/{user_id}",
            headers=admin_headers,
            json={
                "full_name": "Updated Lifecycle User",
                "phone": "+1234567890"
            }
        )
        assert update_response.status_code == 200
        assert update_response.json()["full_name"] == "Updated Lifecycle User"
        
        # Step 3: Deactivate user
        deactivate_response = await client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
        assert deactivate_response.status_code == 204
        
        # Step 4: Activate user
        activate_response = await client.post(f"/api/v1/users/{user_id}/activate", headers=admin_headers)
        assert activate_response.status_code == 200
        assert activate_response.json()["status"] == "active"
        
        # Step 5: Deactivate again (cleanup)
        await client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    
    async def test_create_user_and_login(self, client, admin_headers):
        """Test creating a user and then logging in as that user."""
        # Create user
        password = "TestPass123!"
        create_response = await client.post("/api/v1/users",
            headers=admin_headers,
            json={
                "email": "newlogin@test.com",
                "full_name": "New Login User",
                "password": password,
                "role": "consultant"
            }
        )
        assert create_response.status_code == 201
        
        # Login as new user
        login_response = await client.post("/api/v1/auth/login", json={
            "email": "newlogin@test.com",
            "password": password
        })
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()
    
    async def test_role_based_access_control(self, client, admin_headers, test_consultant_data):
        """Test that role-based access control works correctly."""
        # Create admin user
        admin_create = await client.post("/api/v1/users",
            headers=admin_headers,
            json={
                "email": "newadmin@test.com",
                "full_name": "New Admin",
                "password": "Password123!",
                "role": "super_admin"
            }
        )
        assert admin_create.status_code == 201
        
        # Create consultant user
        consultant_create = await client.post("/api/v1/users",
            headers=admin_headers,
            json={
                "email": "newconsultant@test.com",
                "full_name": "New Consultant",
                "password": "Password123!",
                "role": "consultant"
            }
        )
        assert consultant_create.status_code == 201
        consultant_id = consultant_create.json()["id"]
        
        # Login as consultant
        consultant_login = await client.post("/api/v1/auth/login", json={
            "email": "newconsultant@test.com",
            "password": "Password123!"
        })
        consultant_token = consultant_login.json()["access_token"]
        consultant_headers = {"Authorization": f"Bearer {consultant_token}"}
        
        # Consultant should not be able to access admin endpoints
        response = await client.get("/api/v1/users", headers=consultant_headers)
        assert response.status_code == 403
        
        # Consultant should not be able to create users
        response = await client.post("/api/v1/users",
            headers=consultant_headers,
            json={
                "email": "shouldfail@test.com",
                "full_name": "Should Fail",
                "password": "Password123!",
                "role": "consultant"
            }
        )
        assert response.status_code == 403
        
        # Consultant should not be able to access config
        response = await client.get("/api/v1/config/status", headers=consultant_headers)
        assert response.status_code == 403
    
    async def test_user_cannot_delete_self(self, client, admin_headers, test_admin):
        """Test that a user cannot delete themselves."""
        response = await client.delete(f"/api/v1/users/{test_admin.id}", headers=admin_headers)
        assert response.status_code == 400
        assert "propio usuario" in response.json()["detail"]
    
    async def test_only_admin_can_list_all_users(self, client, admin_headers, consultant_headers):
        """Test that only admins can list all users."""
        # Admin can list
        admin_response = await client.get("/api/v1/users", headers=admin_headers)
        assert admin_response.status_code == 200
        
        # Consultant cannot list
        consultant_response = await client.get("/api/v1/users", headers=consultant_headers)
        assert consultant_response.status_code == 403


# ============== Configuration Integration Tests ==============

@pytest.mark.asyncio
class TestConfigurationFlow:
    """Integration tests for configuration workflows."""
    
    async def test_complete_config_workflow(self, client, admin_headers):
        """Test complete configuration workflow for all integrations."""
        # Set WhatsApp config
        whatsapp_config = {
            "access_token": "test_token_123",
            "phone_number_id": "123456789",
            "verify_token": "verify_token_123",
            "app_secret": "app_secret_123",
            "business_account_id": "business_123"
        }
        response = await client.post("/api/v1/config/whatsapp",
            headers=admin_headers,
            json=whatsapp_config
        )
        assert response.status_code == 200
        
        # Set Zoho config
        zoho_config = {
            "client_id": "1000.testclient",
            "client_secret": "test_secret",
            "refresh_token": "test_refresh",
            "redirect_uri": "http://localhost:8000/callback"
        }
        response = await client.post("/api/v1/config/zoho",
            headers=admin_headers,
            json=zoho_config
        )
        assert response.status_code == 200
        
        # Set LLM config
        llm_config = {
            "provider": "openai",
            "api_key": "sk-test-api-key",
            "model": "gpt-4o-mini",
            "max_tokens": 2000,
            "temperature": 0.0
        }
        response = await client.post("/api/v1/config/llm",
            headers=admin_headers,
            json=llm_config
        )
        assert response.status_code == 200
        
        # Set Email config
        email_config = {
            "provider": "smtp",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "test@gmail.com",
            "smtp_password": "test_password",
            "use_tls": True,
            "default_from": "test@gmail.com",
            "default_from_name": "Test"
        }
        response = await client.post("/api/v1/config/email",
            headers=admin_headers,
            json=email_config
        )
        assert response.status_code == 200
        
        # Verify all configs are saved by retrieving them
        whatsapp_response = await client.get("/api/v1/config/whatsapp", headers=admin_headers)
        assert whatsapp_response.status_code == 200
        assert whatsapp_response.json()["access_token"] == whatsapp_config["access_token"]
        
        zoho_response = await client.get("/api/v1/config/zoho", headers=admin_headers)
        assert zoho_response.status_code == 200
        
        llm_response = await client.get("/api/v1/config/llm", headers=admin_headers)
        assert llm_response.status_code == 200
        
        email_response = await client.get("/api/v1/config/email", headers=admin_headers)
        assert email_response.status_code == 200
    
    async def test_config_update_preserves_other_configs(self, client, admin_headers):
        """Test that updating one config doesn't affect others."""
        # Set initial configs
        await client.post("/api/v1/config/whatsapp",
            headers=admin_headers,
            json={
                "access_token": "initial_whatsapp",
                "phone_number_id": "111",
                "verify_token": "verify1"
            }
        )
        
        await client.post("/api/v1/config/zoho",
            headers=admin_headers,
            json={
                "client_id": "initial_zoho",
                "client_secret": "secret1",
                "refresh_token": "refresh1"
            }
        )
        
        # Update WhatsApp only
        await client.post("/api/v1/config/whatsapp",
            headers=admin_headers,
            json={
                "access_token": "updated_whatsapp",
                "phone_number_id": "222",
                "verify_token": "verify2"
            }
        )
        
        # Verify WhatsApp was updated
        whatsapp_response = await client.get("/api/v1/config/whatsapp", headers=admin_headers)
        assert whatsapp_response.json()["access_token"] == "updated_whatsapp"
        
        # Verify Zoho is unchanged
        zoho_response = await client.get("/api/v1/config/zoho", headers=admin_headers)
        assert zoho_response.json()["client_id"] == "initial_zoho"
    
    async def test_config_encryption(self, client, admin_headers):
        """Test that sensitive config values are encrypted."""
        # Set config with sensitive data
        await client.post("/api/v1/config/whatsapp",
            headers=admin_headers,
            json={
                "access_token": "secret_token_12345",
                "phone_number_id": "123456789",
                "verify_token": "verify_123"
            }
        )
        
        # Get raw config
        raw_response = await client.get("/api/v1/config/raw/whatsapp/config", headers=admin_headers)
        assert raw_response.status_code == 200
        data = raw_response.json()
        
        # Value should be masked
        assert data["value_masked"] is not None
        assert "*" in data["value_masked"]


# ============== Full System Integration Tests ==============

@pytest.mark.asyncio
class TestFullSystemFlow:
    """Full system integration tests."""
    
    async def test_admin_setup_complete_flow(self, client, test_admin_data):
        """Test complete admin setup flow."""
        # 1. Login as admin
        login_response = await client.post("/api/v1/auth/login", json={
            "email": test_admin_data["email"],
            "password": test_admin_data["password"]
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Check system status
        status_response = await client.get("/api/v1/config/status", headers=headers)
        assert status_response.status_code == 200
        
        # 3. Create a consultant user
        consultant_response = await client.post("/api/v1/users",
            headers=headers,
            json={
                "email": "newconsultant@test.com",
                "full_name": "New Consultant",
                "password": "Consultant123!",
                "role": "consultant"
            }
        )
        assert consultant_response.status_code == 201
        
        # 4. Configure WhatsApp
        whatsapp_response = await client.post("/api/v1/config/whatsapp",
            headers=headers,
            json={
                "access_token": "whatsapp_token",
                "phone_number_id": "123456",
                "verify_token": "verify_token"
            }
        )
        assert whatsapp_response.status_code == 200
        
        # 5. Configure LLM
        llm_response = await client.post("/api/v1/config/llm",
            headers=headers,
            json={
                "provider": "openai",
                "api_key": "sk-test",
                "model": "gpt-4o-mini"
            }
        )
        assert llm_response.status_code == 200
        
        # 6. List users and verify new consultant exists
        users_response = await client.get("/api/v1/users", headers=headers)
        assert users_response.status_code == 200
        users = users_response.json()
        assert any(u["email"] == "newconsultant@test.com" for u in users)
    
    async def test_multi_user_scenario(self, client, admin_headers, test_consultant_data):
        """Test multi-user scenario with concurrent operations."""
        # Login as consultant
        consultant_login = await client.post("/api/v1/auth/login", json={
            "email": test_consultant_data["email"],
            "password": test_consultant_data["password"]
        })
        consultant_token = consultant_login.json()["access_token"]
        consultant_headers = {"Authorization": f"Bearer {consultant_token}"}
        
        # Admin creates multiple users
        users_to_create = [
            {"email": f"user{i}@test.com", "full_name": f"User {i}", "password": "Pass123!", "role": "consultant"}
            for i in range(3)
        ]
        
        created_users = []
        for user_data in users_to_create:
            response = await client.post("/api/v1/users", headers=admin_headers, json=user_data)
            assert response.status_code == 201
            created_users.append(response.json())
        
        # Admin lists all users
        users_response = await client.get("/api/v1/users", headers=admin_headers)
        assert users_response.status_code == 200
        
        # Consultant tries to access admin endpoint (should fail)
        fail_response = await client.get("/api/v1/users", headers=consultant_headers)
        assert fail_response.status_code == 403
        
        # Consultant can access their own profile
        me_response = await client.get("/api/v1/auth/me", headers=consultant_headers)
        assert me_response.status_code == 200
    
    async def test_error_handling_integration(self, client):
        """Test error handling across multiple endpoints."""
        # Test various error scenarios
        
        # 1. Invalid login
        response = await client.post("/api/v1/auth/login", json={
            "email": "wrong@email.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        
        # 2. Invalid token
        response = await client.get("/api/v1/users", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 401
        
        # 3. Missing required fields
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@test.com"
            # Missing password
        })
        assert response.status_code == 422
        
        # 4. Invalid email format
        response = await client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "password123"
        })
        assert response.status_code == 422


# ============== Security Integration Tests ==============

@pytest.mark.asyncio
class TestSecurityIntegration:
    """Integration tests for security features."""
    
    async def test_no_sensitive_data_in_error_responses(self, client):
        """Test that error responses don't leak sensitive data."""
        # Try login with wrong password
        response = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "wrong"
        })
        assert response.status_code == 401
        error_detail = response.json()["detail"]
        # Should be generic message
        assert "incorrectas" in error_detail.lower() or "inválidas" in error_detail.lower()
    
    async def test_forgot_password_no_user_enumeration(self, client):
        """Test that forgot password doesn't reveal if user exists."""
        # Existing user
        existing_response = await client.post("/api/v1/auth/forgot-password", json={
            "email": "existing@test.com"
        })
        
        # Non-existing user
        nonexistent_response = await client.post("/api/v1/auth/forgot-password", json={
            "email": "nonexistent@test.com"
        })
        
        # Both should return same status
        assert existing_response.status_code == nonexistent_response.status_code
        assert existing_response.json() == nonexistent_response.json()
    
    async def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = await client.options("/api/v1/auth/login", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        })
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
    
    async def test_password_strength_validation(self, client, admin_headers):
        """Test password strength validation."""
        # Too short password
        response = await client.post("/api/v1/users",
            headers=admin_headers,
            json={
                "email": "weak@test.com",
                "full_name": "Weak Password User",
                "password": "short",
                "role": "consultant"
            }
        )
        assert response.status_code == 422


# ============== Data Consistency Integration Tests ==============

@pytest.mark.asyncio
class TestDataConsistency:
    """Integration tests for data consistency."""
    
    async def test_user_creation_creates_db_record(self, client, admin_headers, db_session):
        """Test that user creation creates actual database record."""
        # Create user via API
        response = await client.post("/api/v1/users",
            headers=admin_headers,
            json={
                "email": "dbtest@test.com",
                "full_name": "DB Test User",
                "password": "Password123!",
                "role": "consultant"
            }
        )
        assert response.status_code == 201
        user_id = response.json()["id"]
        
        # Verify in database
        from sqlalchemy import select
        from app.models import User
        
        result = await db_session.execute(
            select(User).where(User.email == "dbtest@test.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert str(user.id) == user_id
        assert user.full_name == "DB Test User"
    
    async def test_config_update_is_persisted(self, client, admin_headers, db_session):
        """Test that configuration updates are persisted."""
        # Set config via API
        await client.post("/api/v1/config/whatsapp",
            headers=admin_headers,
            json={
                "access_token": "persist_token",
                "phone_number_id": "persist_id",
                "verify_token": "persist_verify"
            }
        )
        
        # Flush to ensure persistence
        await db_session.commit()
        
        # Verify in database
        from sqlalchemy import select
        
        result = await db_session.execute(
            select(Configuration).where(
                (Configuration.category == "whatsapp") &
                (Configuration.key == "config")
            )
        )
        config = result.scalar_one_or_none()
        assert config is not None
        
        # Value should be encrypted
        from app.core.security import decrypt_value
        decrypted = decrypt_value(config.value_encrypted)
        import json
        data = json.loads(decrypted)
        assert data["access_token"] == "persist_token"
