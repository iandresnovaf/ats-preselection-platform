"""Configuración de pytest para tests."""
import pytest
import asyncio
from unittest.mock import MagicMock

# Fixture para el event loop
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Fixture para settings de prueba
@pytest.fixture
def mock_settings_whatsapp_disabled():
    """Settings con WhatsApp deshabilitado."""
    from app.core.config import Settings
    return Settings(
        WHATSAPP_ENABLED=False,
        WHATSAPP_MOCK_MODE=False
    )


@pytest.fixture
def mock_settings_whatsapp_mock():
    """Settings con WhatsApp en modo mock."""
    from app.core.config import Settings
    return Settings(
        WHATSAPP_ENABLED=True,
        WHATSAPP_MOCK_MODE=True
    )
