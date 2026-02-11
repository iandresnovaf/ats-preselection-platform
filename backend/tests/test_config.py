"""
Tests for configuration management endpoints and service.
"""
import pytest
import json
from uuid import uuid4
from unittest.mock import patch, AsyncMock

from app.models import Configuration
from app.schemas import ConfigCategory, WhatsAppConfig, ZohoConfig, LLMConfig, EmailConfig
from app.services.configuration_service import ConfigurationService
from app.core.security import encrypt_value, decrypt_value


pytestmark = pytest.mark.config


# ============== Configuration Service Tests ==============

@pytest.mark.asyncio
class TestConfigurationService:
    """Tests for ConfigurationService class."""
    
    async def test_get_nonexistent_config(self, db_session, user_service):
        """Test getting non-existent configuration."""
        service = ConfigurationService(db_session)
        config = await service.get(ConfigCategory.WHATSAPP, "nonexistent")
        assert config is None
    
    async def test_set_and_get_config(self, db_session):
        """Test setting and getting a configuration."""
        service = ConfigurationService(db_session)
        
        # Set config
        config = await service.set(
            category=ConfigCategory.GENERAL,
            key="test_key",
            value="test_value",
            description="Test configuration"
        )
        
        assert config is not None
        assert config.category == ConfigCategory.GENERAL.value
        assert config.key == "test_key"
        
        # Get config
        retrieved = await service.get(ConfigCategory.GENERAL, "test_key")
        assert retrieved is not None
        assert retrieved.id == config.id
    
    async def test_get_value_encrypted(self, db_session):
        """Test getting decrypted value."""
        service = ConfigurationService(db_session)
        
        await service.set(
            category=ConfigCategory.GENERAL,
            key="secret_key",
            value="secret_value",
            is_encrypted=True
        )
        
        value = await service.get_value(ConfigCategory.GENERAL, "secret_key")
        assert value == "secret_value"
    
    async def test_get_value_not_encrypted(self, db_session):
        """Test getting non-encrypted value."""
        service = ConfigurationService(db_session)
        
        await service.set(
            category=ConfigCategory.GENERAL,
            key="public_key",
            value="public_value",
            is_encrypted=False
        )
        
        value = await service.get_value(ConfigCategory.GENERAL, "public_key")
        assert value == "public_value"
    
    async def test_update_existing_config(self, db_session):
        """Test updating existing configuration."""
        service = ConfigurationService(db_session)
        
        # Create initial config
        await service.set(
            category=ConfigCategory.GENERAL,
            key="update_test",
            value="initial_value"
        )
        
        # Update config
        updated = await service.set(
            category=ConfigCategory.GENERAL,
            key="update_test",
            value="updated_value"
        )
        
        # Verify update
        value = await service.get_value(ConfigCategory.GENERAL, "update_test")
        assert value == "updated_value"
    
    async def test_get_json_value(self, db_session):
        """Test getting JSON configuration."""
        service = ConfigurationService(db_session)
        
        json_data = {"key1": "value1", "key2": 123}
        await service.set_json(
            category=ConfigCategory.GENERAL,
            key="json_test",
            value=json_data
        )
        
        retrieved = await service.get_json_value(ConfigCategory.GENERAL, "json_test")
        assert retrieved == json_data
    
    async def test_get_all_by_category(self, db_session):
        """Test getting all configurations by category."""
        service = ConfigurationService(db_session)
        
        # Create multiple configs in same category
        await service.set(ConfigCategory.WHATSAPP, "key1", "value1")
        await service.set(ConfigCategory.WHATSAPP, "key2", "value2")
        await service.set(ConfigCategory.ZOHO, "key3", "value3")
        
        whatsapp_configs = await service.get_all_by_category(ConfigCategory.WHATSAPP)
        assert len(whatsapp_configs) == 2
        
        zoho_configs = await service.get_all_by_category(ConfigCategory.ZOHO)
        assert len(zoho_configs) == 1
    
    async def test_delete_config(self, db_session):
        """Test deleting configuration."""
        service = ConfigurationService(db_session)
        
        await service.set(ConfigCategory.GENERAL, "to_delete", "value")
        
        result = await service.delete(ConfigCategory.GENERAL, "to_delete")
        assert result is True
        
        # Verify deletion
        config = await service.get(ConfigCategory.GENERAL, "to_delete")
        assert config is None
    
    async def test_delete_nonexistent_config(self, db_session):
        """Test deleting non-existent configuration."""
        service = ConfigurationService(db_session)
        
        result = await service.delete(ConfigCategory.GENERAL, "nonexistent")
        assert result is False


# ============== WhatsApp Configuration Tests ==============

@pytest.mark.asyncio
class TestWhatsAppConfig:
    """Tests for WhatsApp configuration."""
    
    async def test_set_whatsapp_config(self, db_session, test_whatsapp_config, test_admin):
        """Test saving WhatsApp configuration."""
        service = ConfigurationService(db_session)
        config = WhatsAppConfig(**test_whatsapp_config)
        
        result = await service.set_whatsapp_config(config, updated_by=str(test_admin.id))
        assert result is not None
        
        # Verify it can be retrieved
        retrieved = await service.get_whatsapp_config()
        assert retrieved is not None
        assert retrieved.access_token == test_whatsapp_config["access_token"]
        assert retrieved.phone_number_id == test_whatsapp_config["phone_number_id"]
    
    async def test_get_whatsapp_config_none(self, db_session):
        """Test getting WhatsApp config when none exists."""
        service = ConfigurationService(db_session)
        config = await service.get_whatsapp_config()
        assert config is None
    
    async def test_whatsapp_config_model_validation(self, test_whatsapp_config):
        """Test WhatsApp config model validation."""
        # Valid config
        config = WhatsAppConfig(**test_whatsapp_config)
        assert config.access_token == test_whatsapp_config["access_token"]
        
        # Missing required fields should raise error
        with pytest.raises(Exception):
            WhatsAppConfig(phone_number_id="123")  # Missing access_token


# ============== Zoho Configuration Tests ==============

@pytest.mark.asyncio
class TestZohoConfig:
    """Tests for Zoho configuration."""
    
    async def test_set_zoho_config(self, db_session, test_zoho_config, test_admin):
        """Test saving Zoho configuration."""
        service = ConfigurationService(db_session)
        config = ZohoConfig(**test_zoho_config)
        
        result = await service.set_zoho_config(config, updated_by=str(test_admin.id))
        assert result is not None
        
        # Verify it can be retrieved
        retrieved = await service.get_zoho_config()
        assert retrieved is not None
        assert retrieved.client_id == test_zoho_config["client_id"]
    
    async def test_get_zoho_config_none(self, db_session):
        """Test getting Zoho config when none exists."""
        service = ConfigurationService(db_session)
        config = await service.get_zoho_config()
        assert config is None


# ============== LLM Configuration Tests ==============

@pytest.mark.asyncio
class TestLLMConfig:
    """Tests for LLM configuration."""
    
    async def test_set_llm_config(self, db_session, test_llm_config, test_admin):
        """Test saving LLM configuration."""
        service = ConfigurationService(db_session)
        config = LLMConfig(**test_llm_config)
        
        result = await service.set_llm_config(config, updated_by=str(test_admin.id))
        assert result is not None
        
        # Verify it can be retrieved
        retrieved = await service.get_llm_config()
        assert retrieved is not None
        assert retrieved.api_key == test_llm_config["api_key"]
        assert retrieved.model == test_llm_config["model"]
    
    async def test_get_llm_config_none(self, db_session):
        """Test getting LLM config when none exists."""
        service = ConfigurationService(db_session)
        config = await service.get_llm_config()
        assert config is None
    
    async def test_llm_config_temperature_validation(self):
        """Test LLM config temperature validation."""
        # Valid temperature
        config = LLMConfig(api_key="test", temperature=0.5)
        assert config.temperature == 0.5
        
        # Boundary values
        config_min = LLMConfig(api_key="test", temperature=0.0)
        assert config_min.temperature == 0.0
        
        config_max = LLMConfig(api_key="test", temperature=2.0)
        assert config_max.temperature == 2.0
        
        # Invalid temperature should raise error
        with pytest.raises(Exception):
            LLMConfig(api_key="test", temperature=3.0)


# ============== Email Configuration Tests ==============

@pytest.mark.asyncio
class TestEmailConfig:
    """Tests for Email configuration."""
    
    async def test_set_email_config(self, db_session, test_email_config, test_admin):
        """Test saving Email configuration."""
        service = ConfigurationService(db_session)
        config = EmailConfig(**test_email_config)
        
        result = await service.set_email_config(config, updated_by=str(test_admin.id))
        assert result is not None
        
        # Verify it can be retrieved
        retrieved = await service.get_email_config()
        assert retrieved is not None
        assert retrieved.smtp_host == test_email_config["smtp_host"]
    
    async def test_get_email_config_none(self, db_session):
        """Test getting Email config when none exists."""
        service = ConfigurationService(db_session)
        config = await service.get_email_config()
        assert config is None


# ============== Configuration API Endpoint Tests ==============

@pytest.mark.asyncio
class TestConfigEndpoints:
    """Tests for configuration API endpoints."""
    
    # ============== System Status ==============
    
    async def test_get_system_status_as_admin(self, client, admin_headers):
        """Test getting system status as admin."""
        response = await client.get("/api/v1/config/status", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "redis" in data
    
    async def test_get_system_status_unauthorized(self, client):
        """Test getting system status without authentication."""
        response = await client.get("/api/v1/config/status")
        assert response.status_code == 403
    
    # ============== WhatsApp Endpoints ==============
    
    async def test_set_whatsapp_config_as_admin(self, client, admin_headers, test_whatsapp_config):
        """Test setting WhatsApp config as admin."""
        response = await client.post("/api/v1/config/whatsapp", 
            headers=admin_headers,
            json=test_whatsapp_config
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    async def test_set_whatsapp_config_as_consultant(self, client, consultant_headers, test_whatsapp_config):
        """Test setting WhatsApp config as consultant (should fail)."""
        response = await client.post("/api/v1/config/whatsapp", 
            headers=consultant_headers,
            json=test_whatsapp_config
        )
        assert response.status_code == 403
    
    async def test_get_whatsapp_config_as_admin(self, client, admin_headers, test_whatsapp_config):
        """Test getting WhatsApp config as admin."""
        # First set the config
        await client.post("/api/v1/config/whatsapp", 
            headers=admin_headers,
            json=test_whatsapp_config
        )
        
        # Then retrieve it
        response = await client.get("/api/v1/config/whatsapp", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == test_whatsapp_config["access_token"]
    
    async def test_get_whatsapp_config_not_set(self, client, admin_headers):
        """Test getting WhatsApp config when not set."""
        response = await client.get("/api/v1/config/whatsapp", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() is None
    
    async def test_set_whatsapp_config_missing_fields(self, client, admin_headers):
        """Test setting WhatsApp config with missing fields."""
        response = await client.post("/api/v1/config/whatsapp", 
            headers=admin_headers,
            json={"phone_number_id": "123"}  # Missing access_token
        )
        assert response.status_code == 422
    
    # ============== Zoho Endpoints ==============
    
    async def test_set_zoho_config_as_admin(self, client, admin_headers, test_zoho_config):
        """Test setting Zoho config as admin."""
        response = await client.post("/api/v1/config/zoho", 
            headers=admin_headers,
            json=test_zoho_config
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    async def test_get_zoho_config_as_admin(self, client, admin_headers, test_zoho_config):
        """Test getting Zoho config as admin."""
        # First set the config
        await client.post("/api/v1/config/zoho", 
            headers=admin_headers,
            json=test_zoho_config
        )
        
        response = await client.get("/api/v1/config/zoho", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["client_id"] == test_zoho_config["client_id"]
    
    # ============== LLM Endpoints ==============
    
    async def test_set_llm_config_as_admin(self, client, admin_headers, test_llm_config):
        """Test setting LLM config as admin."""
        response = await client.post("/api/v1/config/llm", 
            headers=admin_headers,
            json=test_llm_config
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    async def test_get_llm_config_as_admin(self, client, admin_headers, test_llm_config):
        """Test getting LLM config as admin."""
        await client.post("/api/v1/config/llm", 
            headers=admin_headers,
            json=test_llm_config
        )
        
        response = await client.get("/api/v1/config/llm", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == test_llm_config["provider"]
        assert data["model"] == test_llm_config["model"]
    
    async def test_set_llm_config_invalid_temperature(self, client, admin_headers, test_llm_config):
        """Test setting LLM config with invalid temperature."""
        invalid_config = {**test_llm_config, "temperature": 3.0}
        response = await client.post("/api/v1/config/llm", 
            headers=admin_headers,
            json=invalid_config
        )
        assert response.status_code == 422
    
    # ============== Email Endpoints ==============
    
    async def test_set_email_config_as_admin(self, client, admin_headers, test_email_config):
        """Test setting Email config as admin."""
        response = await client.post("/api/v1/config/email", 
            headers=admin_headers,
            json=test_email_config
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    async def test_get_email_config_as_admin(self, client, admin_headers, test_email_config):
        """Test getting Email config as admin."""
        await client.post("/api/v1/config/email", 
            headers=admin_headers,
            json=test_email_config
        )
        
        response = await client.get("/api/v1/config/email", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["smtp_host"] == test_email_config["smtp_host"]
    
    async def test_set_email_config_invalid_email(self, client, admin_headers, test_email_config):
        """Test setting Email config with invalid email."""
        invalid_config = {**test_email_config, "default_from": "not-an-email"}
        response = await client.post("/api/v1/config/email", 
            headers=admin_headers,
            json=invalid_config
        )
        assert response.status_code == 422
    
    # ============== Raw Config Endpoints ==============
    
    async def test_get_raw_config_as_admin(self, client, admin_headers, test_whatsapp_config):
        """Test getting raw config as admin."""
        # First set the config
        await client.post("/api/v1/config/whatsapp", 
            headers=admin_headers,
            json=test_whatsapp_config
        )
        
        response = await client.get("/api/v1/config/raw/whatsapp/config", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "whatsapp"
        assert data["key"] == "config"
        # Value should be masked for encrypted configs
        assert data["value_masked"] is not None
    
    async def test_get_raw_config_not_found(self, client, admin_headers):
        """Test getting non-existent raw config."""
        response = await client.get("/api/v1/config/raw/nonexistent/key", headers=admin_headers)
        assert response.status_code == 404
    
    async def test_get_raw_config_as_consultant(self, client, consultant_headers):
        """Test getting raw config as consultant (should fail)."""
        response = await client.get("/api/v1/config/raw/whatsapp/config", headers=consultant_headers)
        assert response.status_code == 403


# ============== Configuration Security Tests ==============

@pytest.mark.asyncio
class TestConfigSecurity:
    """Tests for configuration security."""
    
    async def test_sensitive_values_are_encrypted(self, db_session, test_whatsapp_config):
        """Test that sensitive configuration values are encrypted in database."""
        service = ConfigurationService(db_session)
        config = WhatsAppConfig(**test_whatsapp_config)
        
        await service.set_whatsapp_config(config)
        
        # Get raw config from DB
        result = await db_session.execute(
            "SELECT value_encrypted, is_encrypted FROM configurations WHERE key = 'config'"
        )
        row = result.fetchone()
        
        assert row.is_encrypted is True
        # Encrypted value should not be plaintext
        assert row.value_encrypted != json.dumps(test_whatsapp_config)
    
    async def test_non_sensitive_values_can_be_unencrypted(self, db_session):
        """Test that non-sensitive configs can be stored unencrypted."""
        service = ConfigurationService(db_session)
        
        await service.set(
            category=ConfigCategory.GENERAL,
            key="public_setting",
            value="public_value",
            is_encrypted=False
        )
        
        value = await service.get_value(ConfigCategory.GENERAL, "public_setting")
        assert value == "public_value"
    
    async def test_consultant_cannot_access_config_endpoints(self, client, consultant_headers):
        """Test that consultants cannot access any config endpoints."""
        # Try various endpoints
        response = await client.get("/api/v1/config/status", headers=consultant_headers)
        assert response.status_code == 403
        
        response = await client.get("/api/v1/config/whatsapp", headers=consultant_headers)
        assert response.status_code == 403
        
        response = await client.post("/api/v1/config/zoho", 
            headers=consultant_headers,
            json={"test": "value"}
        )
        assert response.status_code == 403


# ============== Configuration Connection Tests ==============

@pytest.mark.asyncio
class TestConfigConnectionTests:
    """Tests for configuration connection testing."""
    
    async def test_test_whatsapp_connection_no_config(self, client, admin_headers):
        """Test WhatsApp connection test with no config."""
        response = await client.post("/api/v1/config/whatsapp/test", headers=admin_headers)
        assert response.status_code == 400
        assert "No hay configuración" in response.json()["detail"]
    
    async def test_test_whatsapp_connection_with_config(self, client, admin_headers, test_whatsapp_config):
        """Test WhatsApp connection test with config."""
        # Set the config first
        await client.post("/api/v1/config/whatsapp", 
            headers=admin_headers,
            json=test_whatsapp_config
        )
        
        response = await client.post("/api/v1/config/whatsapp/test", headers=admin_headers)
        # Will succeed with mock/pending status
        assert response.status_code in [200, 400]
    
    async def test_test_zoho_connection_no_config(self, client, admin_headers):
        """Test Zoho connection test with no config."""
        response = await client.post("/api/v1/config/zoho/test", headers=admin_headers)
        assert response.status_code == 400
        assert "No hay configuración" in response.json()["detail"]
    
    async def test_test_llm_connection_no_config(self, client, admin_headers):
        """Test LLM connection test with no config."""
        response = await client.post("/api/v1/config/llm/test", headers=admin_headers)
        assert response.status_code == 400
        assert "No hay configuración" in response.json()["detail"]
    
    async def test_test_email_connection_no_config(self, client, admin_headers):
        """Test Email connection test with no config."""
        response = await client.post("/api/v1/config/email/test", headers=admin_headers)
        assert response.status_code == 400
        assert "No hay configuración" in response.json()["detail"]
