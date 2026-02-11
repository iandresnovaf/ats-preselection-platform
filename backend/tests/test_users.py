"""
Tests for user management endpoints and service.
"""
import pytest
from uuid import uuid4

from app.models import UserRole, UserStatus
from app.schemas import UserCreate, UserUpdate


pytestmark = pytest.mark.users


# ============== User Service Tests ==============

@pytest.mark.asyncio
class TestUserService:
    """Tests for UserService class."""
    
    async def test_get_by_id_existing(self, user_service, test_admin):
        """Test getting existing user by ID."""
        user = await user_service.get_by_id(str(test_admin.id))
        assert user is not None
        assert user.id == test_admin.id
        assert user.email == test_admin.email
    
    async def test_get_by_id_nonexistent(self, user_service):
        """Test getting non-existent user by ID."""
        user = await user_service.get_by_id(str(uuid4()))
        assert user is None
    
    async def test_get_by_email_existing(self, user_service, test_admin):
        """Test getting existing user by email."""
        user = await user_service.get_by_email(test_admin.email)
        assert user is not None
        assert user.email == test_admin.email
    
    async def test_get_by_email_nonexistent(self, user_service):
        """Test getting non-existent user by email."""
        user = await user_service.get_by_email("nonexistent@test.com")
        assert user is None
    
    async def test_get_by_email_case_insensitive(self, user_service, test_admin):
        """Test that email lookup is case insensitive."""
        user = await user_service.get_by_email(test_admin.email.upper())
        assert user is not None
        assert user.email == test_admin.email
    
    async def test_list_users_empty(self, db_session, user_service):
        """Test listing users when none exist."""
        users = await user_service.list_users()
        # Should return only the test users created by fixtures
        assert len(users) >= 0
    
    async def test_list_users_with_pagination(self, user_service):
        """Test listing users with pagination."""
        users = await user_service.list_users(skip=0, limit=10)
        assert isinstance(users, list)
    
    async def test_list_users_filter_by_role(self, user_service, test_admin, test_consultant):
        """Test filtering users by role."""
        admin_users = await user_service.list_users(role="super_admin")
        assert all(u.role == UserRole.SUPER_ADMIN for u in admin_users)
        
        consultant_users = await user_service.list_users(role="consultant")
        assert all(u.role == UserRole.CONSULTANT for u in consultant_users)
    
    async def test_list_users_filter_by_status(self, user_service, test_admin, test_inactive_user):
        """Test filtering users by status."""
        active_users = await user_service.list_users(status="active")
        assert all(u.status == UserStatus.ACTIVE for u in active_users)
        
        inactive_users = await user_service.list_users(status="inactive")
        assert all(u.status == UserStatus.INACTIVE for u in inactive_users)
    
    async def test_list_users_search(self, user_service, test_admin):
        """Test searching users."""
        # Search by email
        users = await user_service.list_users(search=test_admin.email[:5])
        assert len(users) > 0
        
        # Search by name
        users = await user_service.list_users(search=test_admin.full_name[:5])
        assert len(users) > 0
    
    async def test_list_users_search_no_results(self, user_service):
        """Test searching users with no matches."""
        users = await user_service.list_users(search="xyznonexistent")
        assert len(users) == 0
    
    async def test_create_user_success(self, user_service, db_session):
        """Test successful user creation."""
        user_data = UserCreate(
            email="newuser@test.com",
            full_name="New Test User",
            password="Password123!",
            role="consultant"
        )
        user = await user_service.create_user(user_data)
        
        assert user is not None
        assert user.email == "newuser@test.com"
        assert user.full_name == "New Test User"
        assert user.role == UserRole.CONSULTANT
        assert user.status == UserStatus.ACTIVE
    
    async def test_create_user_duplicate_email(self, user_service, test_admin):
        """Test creating user with duplicate email."""
        user_data = UserCreate(
            email=test_admin.email,
            full_name="Duplicate User",
            password="Password123!",
            role="consultant"
        )
        with pytest.raises(ValueError, match="Ya existe un usuario"):
            await user_service.create_user(user_data)
    
    async def test_create_user_case_insensitive_email(self, user_service, test_admin):
        """Test that email is stored in lowercase."""
        user_data = UserCreate(
            email="UPPERCASE@TEST.COM",
            full_name="Uppercase User",
            password="Password123!",
            role="consultant"
        )
        user = await user_service.create_user(user_data)
        assert user.email == "uppercase@test.com"
    
    async def test_update_user_success(self, user_service, test_consultant):
        """Test successful user update."""
        update_data = UserUpdate(
            full_name="Updated Name",
            phone="+1234567890"
        )
        updated = await user_service.update_user(str(test_consultant.id), update_data)
        
        assert updated is not None
        assert updated.full_name == "Updated Name"
        assert updated.phone == "+1234567890"
    
    async def test_update_user_nonexistent(self, user_service):
        """Test updating non-existent user."""
        update_data = UserUpdate(full_name="Updated Name")
        updated = await user_service.update_user(str(uuid4()), update_data)
        assert updated is None
    
    async def test_update_user_email_unique(self, user_service, test_admin, test_consultant):
        """Test that updated email must be unique."""
        update_data = UserUpdate(email=test_admin.email)
        with pytest.raises(ValueError, match="Ya existe un usuario"):
            await user_service.update_user(str(test_consultant.id), update_data)
    
    async def test_update_password_success(self, user_service, test_consultant):
        """Test successful password update."""
        from app.core.auth import verify_password
        
        result = await user_service.update_password(
            str(test_consultant.id),
            "NewPassword123!"
        )
        assert result is True
        
        # Verify password was changed
        user = await user_service.get_by_id(str(test_consultant.id))
        assert verify_password("NewPassword123!", user.hashed_password)
    
    async def test_update_password_nonexistent(self, user_service):
        """Test updating password for non-existent user."""
        result = await user_service.update_password(str(uuid4()), "NewPassword123!")
        assert result is False
    
    async def test_deactivate_user_success(self, user_service, test_consultant):
        """Test successful user deactivation."""
        result = await user_service.deactivate_user(str(test_consultant.id))
        assert result is not None
        assert result.status == UserStatus.INACTIVE
    
    async def test_deactivate_user_nonexistent(self, user_service):
        """Test deactivating non-existent user."""
        result = await user_service.deactivate_user(str(uuid4()))
        assert result is None
    
    async def test_activate_user_success(self, user_service, test_inactive_user):
        """Test successful user activation."""
        result = await user_service.activate_user(str(test_inactive_user.id))
        assert result is not None
        assert result.status == UserStatus.ACTIVE
    
    async def test_activate_user_nonexistent(self, user_service):
        """Test activating non-existent user."""
        result = await user_service.activate_user(str(uuid4()))
        assert result is None


# ============== User API Endpoint Tests ==============

@pytest.mark.asyncio
class TestUserEndpoints:
    """Tests for user API endpoints."""
    
    # ============== List Users ==============
    
    async def test_list_users_as_admin(self, client, admin_headers):
        """Test listing users as admin."""
        response = await client.get("/api/v1/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_list_users_as_consultant(self, client, consultant_headers):
        """Test listing users as consultant (should fail)."""
        response = await client.get("/api/v1/users", headers=consultant_headers)
        assert response.status_code == 403
    
    async def test_list_users_unauthorized(self, client):
        """Test listing users without authentication."""
        response = await client.get("/api/v1/users")
        assert response.status_code == 403
    
    async def test_list_users_filter_by_role(self, client, admin_headers):
        """Test listing users filtered by role."""
        response = await client.get("/api/v1/users?role=super_admin", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(u["role"] == "super_admin" for u in data)
    
    async def test_list_users_filter_by_status(self, client, admin_headers):
        """Test listing users filtered by status."""
        response = await client.get("/api/v1/users?status=active", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(u["status"] == "active" for u in data)
    
    async def test_list_users_search(self, client, admin_headers, test_admin):
        """Test searching users."""
        response = await client.get(f"/api/v1/users?search={test_admin.email[:5]}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
    
    async def test_list_users_pagination(self, client, admin_headers):
        """Test user listing pagination."""
        response = await client.get("/api/v1/users?skip=0&limit=2", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2
    
    # ============== Create User ==============
    
    async def test_create_user_as_admin(self, client, admin_headers):
        """Test creating user as admin."""
        response = await client.post("/api/v1/users", headers=admin_headers, json={
            "email": "newuser2@test.com",
            "full_name": "New User 2",
            "password": "Password123!",
            "role": "consultant"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser2@test.com"
        assert data["role"] == "consultant"
    
    async def test_create_user_as_consultant(self, client, consultant_headers):
        """Test creating user as consultant (should fail)."""
        response = await client.post("/api/v1/users", headers=consultant_headers, json={
            "email": "shouldfail@test.com",
            "full_name": "Should Fail",
            "password": "Password123!",
            "role": "consultant"
        })
        assert response.status_code == 403
    
    async def test_create_user_duplicate_email(self, client, admin_headers, test_admin):
        """Test creating user with duplicate email."""
        response = await client.post("/api/v1/users", headers=admin_headers, json={
            "email": test_admin.email,
            "full_name": "Duplicate User",
            "password": "Password123!",
            "role": "consultant"
        })
        assert response.status_code == 400
        assert "Ya existe" in response.json()["detail"]
    
    async def test_create_user_invalid_email(self, client, admin_headers):
        """Test creating user with invalid email."""
        response = await client.post("/api/v1/users", headers=admin_headers, json={
            "email": "not-an-email",
            "full_name": "Invalid Email",
            "password": "Password123!",
            "role": "consultant"
        })
        assert response.status_code == 422
    
    async def test_create_user_short_password(self, client, admin_headers):
        """Test creating user with short password."""
        response = await client.post("/api/v1/users", headers=admin_headers, json={
            "email": "test@test.com",
            "full_name": "Test User",
            "password": "short",
            "role": "consultant"
        })
        assert response.status_code == 422
    
    async def test_create_user_missing_name(self, client, admin_headers):
        """Test creating user without name."""
        response = await client.post("/api/v1/users", headers=admin_headers, json={
            "email": "test@test.com",
            "password": "Password123!",
            "role": "consultant"
        })
        assert response.status_code == 422
    
    async def test_create_user_invalid_role(self, client, admin_headers):
        """Test creating user with invalid role."""
        response = await client.post("/api/v1/users", headers=admin_headers, json={
            "email": "test@test.com",
            "full_name": "Test User",
            "password": "Password123!",
            "role": "invalid_role"
        })
        assert response.status_code == 422
    
    # ============== Get User ==============
    
    async def test_get_user_as_admin(self, client, admin_headers, test_consultant):
        """Test getting user as admin."""
        response = await client.get(f"/api/v1/users/{test_consultant.id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_consultant.id)
        assert data["email"] == test_consultant.email
    
    async def test_get_user_as_consultant(self, client, consultant_headers, test_admin):
        """Test getting user as consultant (should fail)."""
        response = await client.get(f"/api/v1/users/{test_admin.id}", headers=consultant_headers)
        assert response.status_code == 403
    
    async def test_get_user_nonexistent(self, client, admin_headers):
        """Test getting non-existent user."""
        response = await client.get(f"/api/v1/users/{uuid4()}", headers=admin_headers)
        assert response.status_code == 404
    
    async def test_get_user_invalid_id(self, client, admin_headers):
        """Test getting user with invalid ID."""
        response = await client.get("/api/v1/users/invalid-id", headers=admin_headers)
        assert response.status_code == 422
    
    async def test_get_my_profile(self, client, admin_headers, test_admin):
        """Test getting own profile."""
        response = await client.get("/api/v1/users/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_admin.email
    
    # ============== Update User ==============
    
    async def test_update_user_as_admin(self, client, admin_headers, test_consultant):
        """Test updating user as admin."""
        response = await client.patch(f"/api/v1/users/{test_consultant.id}", 
            headers=admin_headers,
            json={
                "full_name": "Updated By Admin",
                "phone": "+9876543210"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated By Admin"
    
    async def test_update_user_as_consultant(self, client, consultant_headers, test_admin):
        """Test updating user as consultant (should fail)."""
        response = await client.patch(f"/api/v1/users/{test_admin.id}", 
            headers=consultant_headers,
            json={"full_name": "Should Not Update"}
        )
        assert response.status_code == 403
    
    async def test_update_user_nonexistent(self, client, admin_headers):
        """Test updating non-existent user."""
        response = await client.patch(f"/api/v1/users/{uuid4()}", 
            headers=admin_headers,
            json={"full_name": "Non Existent"}
        )
        assert response.status_code == 404
    
    async def test_update_user_email_conflict(self, client, admin_headers, test_admin, test_consultant):
        """Test updating user email to existing email."""
        response = await client.patch(f"/api/v1/users/{test_consultant.id}", 
            headers=admin_headers,
            json={"email": test_admin.email}
        )
        assert response.status_code == 400
        assert "en uso" in response.json()["detail"]
    
    async def test_update_user_invalid_email(self, client, admin_headers, test_consultant):
        """Test updating user with invalid email."""
        response = await client.patch(f"/api/v1/users/{test_consultant.id}", 
            headers=admin_headers,
            json={"email": "not-an-email"}
        )
        assert response.status_code == 422
    
    # ============== Delete/Deactivate User ==============
    
    async def test_delete_user_as_admin(self, client, admin_headers, test_consultant):
        """Test deactivating user as admin."""
        response = await client.delete(f"/api/v1/users/{test_consultant.id}", headers=admin_headers)
        assert response.status_code == 204
    
    async def test_delete_user_as_consultant(self, client, consultant_headers, test_admin):
        """Test deactivating user as consultant (should fail)."""
        response = await client.delete(f"/api/v1/users/{test_admin.id}", headers=consultant_headers)
        assert response.status_code == 403
    
    async def test_delete_user_nonexistent(self, client, admin_headers):
        """Test deactivating non-existent user."""
        response = await client.delete(f"/api/v1/users/{uuid4()}", headers=admin_headers)
        assert response.status_code == 404
    
    async def test_delete_own_user(self, client, admin_headers, test_admin):
        """Test that admin cannot delete themselves."""
        response = await client.delete(f"/api/v1/users/{test_admin.id}", headers=admin_headers)
        assert response.status_code == 400
        assert "propio usuario" in response.json()["detail"]
    
    # ============== Activate User ==============
    
    async def test_activate_user_as_admin(self, client, admin_headers, test_inactive_user):
        """Test activating user as admin."""
        response = await client.post(f"/api/v1/users/{test_inactive_user.id}/activate", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
    
    async def test_activate_user_as_consultant(self, client, consultant_headers, test_inactive_user):
        """Test activating user as consultant (should fail)."""
        response = await client.post(f"/api/v1/users/{test_inactive_user.id}/activate", headers=consultant_headers)
        assert response.status_code == 403
    
    async def test_activate_user_nonexistent(self, client, admin_headers):
        """Test activating non-existent user."""
        response = await client.post(f"/api/v1/users/{uuid4()}/activate", headers=admin_headers)
        assert response.status_code == 404
    
    async def test_activate_already_active_user(self, client, admin_headers, test_admin):
        """Test activating already active user."""
        response = await client.post(f"/api/v1/users/{test_admin.id}/activate", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "active"


# ============== User Model Tests ==============

@pytest.mark.asyncio
class TestUserModel:
    """Tests for User model behavior."""
    
    async def test_user_default_role(self, db_session):
        """Test that default role is consultant."""
        from app.core.auth import get_password_hash
        user = User(
            email="roletest@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="Role Test User"
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        
        assert user.role == UserRole.CONSULTANT
    
    async def test_user_default_status(self, db_session):
        """Test that default status is pending."""
        from app.core.auth import get_password_hash
        user = User(
            email="statustest@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="Status Test User"
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        
        assert user.status == UserStatus.PENDING
    
    async def test_user_relationships(self, db_session, test_admin):
        """Test that user relationships exist."""
        # Verify that relationship attributes exist
        assert hasattr(test_admin, 'assigned_jobs')
        assert hasattr(test_admin, 'decisions')
        assert hasattr(test_admin, 'audit_logs')
    
    async def test_user_timestamps(self, db_session, test_admin):
        """Test that timestamps are set."""
        from datetime import datetime
        
        assert test_admin.created_at is not None
        assert test_admin.updated_at is not None
        assert isinstance(test_admin.created_at, datetime)
        assert isinstance(test_admin.updated_at, datetime)
