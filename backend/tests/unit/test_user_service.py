"""
Unit tests for UserService.
"""
import pytest
from fastapi import HTTPException

from app.services.user_service import UserService
from app.schemas import UserCreate, UserUpdate
from app.models import UserRole, UserStatus


class TestUserService:
    """Tests for UserService."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, db_session):
        """Test creating a new user."""
        service = UserService(db_session)
        
        user_data = UserCreate(
            email="newuser@test.com",
            full_name="New User",
            password="SecurePass123!",
            role="consultant",
        )
        
        user = await service.create(user_data)
        
        assert user is not None
        assert user.email == "newuser@test.com"
        assert user.full_name == "New User"
        assert user.role == UserRole.CONSULTANT
        assert user.status == UserStatus.PENDING  # Default status
        assert user.hashed_password is not None
        assert user.hashed_password != "SecurePass123!"  # Password should be hashed
    
    @pytest.mark.asyncio
    async def test_create_user_with_role_viewer(self, db_session):
        """Test creating a user with viewer role."""
        service = UserService(db_session)
        
        user_data = UserCreate(
            email="vieweruser@test.com",
            full_name="Viewer User",
            password="SecurePass123!",
            role="viewer",
        )
        
        user = await service.create(user_data)
        
        assert user is not None
        assert user.role == UserRole.VIEWER
    
    @pytest.mark.asyncio
    async def test_create_duplicate_user(self, db_session, test_admin):
        """Test creating a user with duplicate email."""
        service = UserService(db_session)
        
        user_data = UserCreate(
            email=test_admin.email,  # Duplicate email
            full_name="Another User",
            password="SecurePass123!",
            role="consultant",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await service.create(user_data)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session, test_admin):
        """Test getting user by ID."""
        service = UserService(db_session)
        
        user = await service.get_by_id(str(test_admin.id))
        
        assert user is not None
        assert user.id == test_admin.id
        assert user.email == test_admin.email
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session):
        """Test getting non-existent user by ID."""
        service = UserService(db_session)
        
        user = await service.get_by_id("12345678-1234-1234-1234-123456789abc")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_by_email(self, db_session, test_admin):
        """Test getting user by email."""
        service = UserService(db_session)
        
        user = await service.get_by_email(test_admin.email)
        
        assert user is not None
        assert user.email == test_admin.email
    
    @pytest.mark.asyncio
    async def test_list_users(self, db_session, test_admin, test_consultant):
        """Test listing all users."""
        service = UserService(db_session)
        
        users = await service.list_users()
        
        assert len(users) >= 2
        emails = [u.email for u in users]
        assert test_admin.email in emails
        assert test_consultant.email in emails
    
    @pytest.mark.asyncio
    async def test_update_user(self, db_session, test_consultant):
        """Test updating a user."""
        service = UserService(db_session)
        
        update_data = UserUpdate(
            full_name="Updated Name",
            phone="+9876543210",
        )
        
        updated = await service.update(str(test_consultant.id), update_data.model_dump(exclude_unset=True))
        
        assert updated is not None
        assert updated.full_name == "Updated Name"
        assert updated.phone == "+9876543210"
    
    @pytest.mark.asyncio
    async def test_update_password(self, db_session, test_consultant):
        """Test updating user password."""
        service = UserService(db_session)
        
        old_hash = test_consultant.hashed_password
        await service.update_password(str(test_consultant.id), "NewSecurePass123!")
        
        # Refresh user from DB
        await db_session.refresh(test_consultant)
        
        assert test_consultant.hashed_password != old_hash
    
    @pytest.mark.asyncio
    async def test_delete_user(self, db_session):
        """Test deleting a user."""
        service = UserService(db_session)
        
        # Create a user to delete
        user_data = UserCreate(
            email="todelete@test.com",
            full_name="To Delete",
            password="SecurePass123!",
            role="consultant",
        )
        user = await service.create(user_data)
        
        # Delete the user
        success = await service.delete(str(user.id))
        
        assert success is True
        
        # Verify user is deleted
        deleted = await service.get_by_id(str(user.id))
        assert deleted is None
    
    @pytest.mark.asyncio
    async def test_change_status(self, db_session, test_consultant):
        """Test changing user status."""
        service = UserService(db_session)
        
        assert test_consultant.status == UserStatus.ACTIVE
        
        updated = await service.change_status(str(test_consultant.id), "inactive")
        
        assert updated is not None
        assert updated.status == UserStatus.INACTIVE
    
    @pytest.mark.asyncio
    async def test_change_role(self, db_session, test_consultant):
        """Test changing user role."""
        service = UserService(db_session)
        
        assert test_consultant.role == UserRole.CONSULTANT
        
        updated = await service.change_role(str(test_consultant.id), "viewer")
        
        assert updated is not None
        assert updated.role == UserRole.VIEWER
