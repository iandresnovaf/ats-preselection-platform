"""
Test configuration and fixtures for ATS Platform backend tests.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import String
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

# Import app components
import sys
sys.path.insert(0, '/home/andres/.openclaw/workspace/ats-platform/backend')

# UUID Compatibility Layer for SQLite
# PostgreSQL uses UUID type, SQLite doesn't support it natively
import uuid
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID

class CompatibleUUID(String):
    """UUID type compatible with both PostgreSQL and SQLite."""
    def __init__(self, as_uuid=False, *args, **kwargs):
        super().__init__(36, *args, **kwargs)
        self.as_uuid = as_uuid
    
    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if isinstance(value, uuid.UUID):
                return str(value)
            return value
        return process
    
    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            if self.as_uuid:
                return uuid.UUID(value)
            return value
        return process

# Monkey-patch UUID before importing models
import app.core.database as db_module
original_uuid = getattr(db_module, 'UUID', None)
db_module.UUID = CompatibleUUID

import app.models as models_module
models_module.UUID = CompatibleUUID

from app.main import app
from app.core.database import Base, get_db
from app.core.auth import get_password_hash, create_access_token, create_refresh_token
from app.core.config import Settings
from app.models import User, UserRole, UserStatus, Configuration
from app.schemas import UserCreate
from app.services.user_service import UserService


# ============== Test Database Configuration ==============

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    # Ensure UUID is patched before creating engine
    db_module.UUID = CompatibleUUID
    models_module.UUID = CompatibleUUID
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Start nested transaction
        await session.begin_nested()
        
        yield session
        
        # Rollback the nested transaction
        await session.rollback()
        await session.close()


@pytest.fixture
def override_get_db(db_session):
    """Override the get_db dependency for testing."""
    async def _get_db():
        yield db_session
    return _get_db


@pytest.fixture
async def client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database override."""
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# ============== Test Data Fixtures ==============

@pytest.fixture
def test_password() -> str:
    """Return a test password."""
    return "TestPassword123!"


@pytest.fixture
def test_admin_data(test_password) -> dict:
    """Return test admin user data."""
    return {
        "email": "admin@test.com",
        "full_name": "Test Admin",
        "password": test_password,
        "role": "super_admin",
        "status": "active",
    }


@pytest.fixture
def test_consultant_data(test_password) -> dict:
    """Return test consultant user data."""
    return {
        "email": "consultant@test.com",
        "full_name": "Test Consultant",
        "password": test_password,
        "role": "consultant",
        "status": "active",
    }


@pytest.fixture
def test_pending_user_data(test_password) -> dict:
    """Return test pending user data."""
    return {
        "email": "pending@test.com",
        "full_name": "Test Pending User",
        "password": test_password,
        "role": "consultant",
        "status": "pending",
    }


@pytest.fixture
def test_inactive_user_data(test_password) -> dict:
    """Return test inactive user data."""
    return {
        "email": "inactive@test.com",
        "full_name": "Test Inactive User",
        "password": test_password,
        "role": "consultant",
        "status": "inactive",
    }


# ============== User Fixtures ==============

@pytest.fixture
async def test_admin(db_session, test_admin_data) -> User:
    """Create a test admin user."""
    user = User(
        email=test_admin_data["email"],
        hashed_password=get_password_hash(test_admin_data["password"]),
        full_name=test_admin_data["full_name"],
        role=UserRole.SUPER_ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_consultant(db_session, test_consultant_data) -> User:
    """Create a test consultant user."""
    user = User(
        email=test_consultant_data["email"],
        hashed_password=get_password_hash(test_consultant_data["password"]),
        full_name=test_consultant_data["full_name"],
        role=UserRole.CONSULTANT,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_pending_user(db_session, test_pending_user_data) -> User:
    """Create a test pending user."""
    user = User(
        email=test_pending_user_data["email"],
        hashed_password=get_password_hash(test_pending_user_data["password"]),
        full_name=test_pending_user_data["full_name"],
        role=UserRole.CONSULTANT,
        status=UserStatus.PENDING,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_inactive_user(db_session, test_inactive_user_data) -> User:
    """Create a test inactive user."""
    user = User(
        email=test_inactive_user_data["email"],
        hashed_password=get_password_hash(test_inactive_user_data["password"]),
        full_name=test_inactive_user_data["full_name"],
        role=UserRole.CONSULTANT,
        status=UserStatus.INACTIVE,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


# ============== Token Fixtures ==============

@pytest.fixture
def admin_token(test_admin) -> str:
    """Generate an access token for the test admin."""
    return create_access_token(data={"sub": str(test_admin.id)})


@pytest.fixture
def admin_refresh_token(test_admin) -> str:
    """Generate a refresh token for the test admin."""
    return create_refresh_token(data={"sub": str(test_admin.id)})


@pytest.fixture
def consultant_token(test_consultant) -> str:
    """Generate an access token for the test consultant."""
    return create_access_token(data={"sub": str(test_consultant.id)})


@pytest.fixture
def pending_user_token(test_pending_user) -> str:
    """Generate an access token for the test pending user."""
    return create_access_token(data={"sub": str(test_pending_user.id)})


@pytest.fixture
def inactive_user_token(test_inactive_user) -> str:
    """Generate an access token for the test inactive user."""
    return create_access_token(data={"sub": str(test_inactive_user.id)})


@pytest.fixture
def expired_token(test_admin) -> str:
    """Generate an expired access token."""
    expire = datetime.utcnow() - timedelta(minutes=1)
    from jose import jwt
    from app.core.config import settings
    to_encode = {"sub": str(test_admin.id), "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.fixture
def invalid_token() -> str:
    """Return an invalid token."""
    return "invalid.token.here"


# ============== Authentication Headers ==============

@pytest.fixture
def admin_headers(admin_token) -> dict:
    """Return authorization headers for admin."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def consultant_headers(consultant_token) -> dict:
    """Return authorization headers for consultant."""
    return {"Authorization": f"Bearer {consultant_token}"}


@pytest.fixture
def pending_user_headers(pending_user_token) -> dict:
    """Return authorization headers for pending user."""
    return {"Authorization": f"Bearer {pending_user_token}"}


@pytest.fixture
def inactive_user_headers(inactive_user_token) -> dict:
    """Return authorization headers for inactive user."""
    return {"Authorization": f"Bearer {inactive_user_token}"}


# ============== Service Fixtures ==============

@pytest.fixture
def user_service(db_session) -> UserService:
    """Return a UserService instance."""
    return UserService(db_session)


# ============== Mock Fixtures ==============

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.ping.return_value = True
    return mock


@pytest.fixture
def mock_email_service():
    """Mock email service."""
    mock = AsyncMock()
    mock.send_email.return_value = True
    return mock


@pytest.fixture
def mock_whatsapp_service():
    """Mock WhatsApp service."""
    mock = AsyncMock()
    mock.send_message.return_value = True
    return mock


@pytest.fixture
def mock_zoho_service():
    """Mock Zoho service."""
    mock = AsyncMock()
    mock.sync_candidate.return_value = {"id": "zoho123"}
    mock.sync_job.return_value = {"id": "job123"}
    return mock


# ============== Configuration Fixtures ==============

@pytest.fixture
def test_whatsapp_config() -> dict:
    """Return test WhatsApp configuration."""
    return {
        "access_token": "test_access_token_12345",
        "phone_number_id": "123456789",
        "verify_token": "test_verify_token",
        "app_secret": "test_app_secret",
        "business_account_id": "business_123",
    }


@pytest.fixture
def test_zoho_config() -> dict:
    """Return test Zoho configuration."""
    return {
        "client_id": "1000.testclientid",
        "client_secret": "test_client_secret",
        "refresh_token": "test_refresh_token",
        "redirect_uri": "http://localhost:8000/api/v1/zoho/callback",
        "job_id_field": "Job_Opening_ID",
        "candidate_id_field": "Candidate_ID",
        "stage_field": "Stage",
    }


@pytest.fixture
def test_llm_config() -> dict:
    """Return test LLM configuration."""
    return {
        "provider": "openai",
        "api_key": "sk-test-api-key-12345",
        "model": "gpt-4o-mini",
        "max_tokens": 2000,
        "temperature": 0.0,
        "prompt_version": "v1.0",
    }


@pytest.fixture
def test_email_config() -> dict:
    """Return test Email configuration."""
    return {
        "provider": "smtp",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "test@example.com",
        "smtp_password": "test_password",
        "use_tls": True,
        "default_from": "test@example.com",
        "default_from_name": "Test Sender",
    }


# ============== pytest-mock Fixture ==============

@pytest.fixture
def mocker():
    """Provide pytest-mock fixture."""
    from unittest.mock import Mock, AsyncMock, patch, MagicMock
    
    class Mocker:
        def patch(self, target, **kwargs):
            return patch(target, **kwargs)
        
        def Mock(self, *args, **kwargs):
            return Mock(*args, **kwargs)
        
        def AsyncMock(self, *args, **kwargs):
            return AsyncMock(*args, **kwargs)
        
        def MagicMock(self, *args, **kwargs):
            return MagicMock(*args, **kwargs)
    
    return Mocker()
