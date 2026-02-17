"""Tests para el servicio de WhatsApp Business API."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.whatsapp_service import WhatsAppService


@pytest.fixture
def mock_settings():
    """Fixture para settings mockeados."""
    with patch('app.services.whatsapp_service.settings') as mock:
        mock.WHATSAPP_ACCESS_TOKEN = "test_token"
        mock.WHATSAPP_PHONE_NUMBER_ID = "123456789"
        mock.WHATSAPP_BUSINESS_ACCOUNT_ID = "987654321"
        mock.WHATSAPP_API_VERSION = "v18.0"
        mock.WHATSAPP_WEBHOOK_VERIFY_TOKEN = "test_verify_token"
        mock.WHATSAPP_APP_SECRET = "test_app_secret"
        mock.WHATSAPP_MOCK_MODE = False
        yield mock


@pytest.fixture
def whatsapp_service(mock_settings):
    """Fixture para el servicio de WhatsApp."""
    return WhatsAppService()


@pytest.fixture
def mock_whatsapp_service(mock_settings):
    """Fixture para el servicio de WhatsApp en modo mock."""
    mock_settings.WHATSAPP_MOCK_MODE = True
    return WhatsAppService()


class TestWhatsAppService:
    """Tests para WhatsAppService."""
    
    def test_format_phone_number(self, whatsapp_service):
        """Test de formateo de números de teléfono."""
        # Con +
        assert whatsapp_service._format_phone_number("+57 300 123 4567") == "573001234567"
        # Sin +
        assert whatsapp_service._format_phone_number("573001234567") == "573001234567"
        # Con espacios y guiones
        assert whatsapp_service._format_phone_number("300-123-4567") == "3001234567"
        # Con paréntesis
        assert whatsapp_service._format_phone_number("(300) 123-4567") == "3001234567"
    
    def test_get_auth_headers(self, whatsapp_service):
        """Test de generación de headers de autenticación."""
        headers = whatsapp_service._get_auth_headers()
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Content-Type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_send_template_message_mock(self, mock_whatsapp_service):
        """Test de envío de mensaje de template en modo mock."""
        result = await mock_whatsapp_service.send_template_message(
            to_phone="573001234567",
            template_name="contacto_inicial",
            language_code="es",
            components=[]
        )
        
        assert result["success"] is True
        assert result["mock"] is True
        assert "message_id" in result
        assert result["template"] == "contacto_inicial"
    
    @pytest.mark.asyncio
    async def test_send_text_message_mock(self, mock_whatsapp_service):
        """Test de envío de mensaje de texto en modo mock."""
        result = await mock_whatsapp_service.send_text_message(
            to_phone="573001234567",
            message="Hola, ¿cómo estás?"
        )
        
        assert result["success"] is True
        assert result["mock"] is True
        assert "message_id" in result
    
    @pytest.mark.asyncio
    async def test_get_message_status_mock(self, mock_whatsapp_service):
        """Test de obtención de estado en modo mock."""
        result = await mock_whatsapp_service.get_message_status("mock_message_id")
        
        assert result["success"] is True
        assert result["mock"] is True
        assert result["status"] == "read"
    
    def test_verify_webhook_success(self, whatsapp_service):
        """Test de verificación exitosa de webhook."""
        challenge = "test_challenge_123"
        result = whatsapp_service.verify_webhook(
            mode="subscribe",
            token="test_verify_token",
            challenge=challenge
        )
        
        assert result == challenge
    
    def test_verify_webhook_failure(self, whatsapp_service):
        """Test de verificación fallida de webhook."""
        result = whatsapp_service.verify_webhook(
            mode="subscribe",
            token="wrong_token",
            challenge="test_challenge"
        )
        
        assert result is None
    
    def test_verify_webhook_wrong_mode(self, whatsapp_service):
        """Test de verificación con modo incorrecto."""
        result = whatsapp_service.verify_webhook(
            mode="unsubscribe",
            token="test_verify_token",
            challenge="test_challenge"
        )
        
        assert result is None
    
    def test_verify_webhook_signature_valid(self, whatsapp_service):
        """Test de verificación de firma válida."""
        import hmac
        import hashlib
        
        body = b'{"test": "data"}'
        expected_signature = hmac.new(
            b"test_app_secret",
            body,
            hashlib.sha256
        ).hexdigest()
        
        result = whatsapp_service.verify_webhook_signature(
            body=body,
            signature=f"sha256={expected_signature}"
        )
        
        assert result is True
    
    def test_verify_webhook_signature_invalid(self, whatsapp_service):
        """Test de verificación de firma inválida."""
        body = b'{"test": "data"}'
        
        result = whatsapp_service.verify_webhook_signature(
            body=body,
            signature="sha256=invalid_signature"
        )
        
        assert result is False
    
    def test_verify_webhook_signature_no_secret(self, whatsapp_service, mock_settings):
        """Test de verificación sin App Secret configurado."""
        mock_settings.WHATSAPP_APP_SECRET = None
        
        body = b'{"test": "data"}'
        result = whatsapp_service.verify_webhook_signature(
            body=body,
            signature="sha256=some_signature"
        )
        
        # Sin App Secret, retorna True (omite verificación)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_process_incoming_message_text(self, whatsapp_service):
        """Test de procesamiento de mensaje de texto entrante."""
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [{
                            "id": "wamid.test123",
                            "from": "573001234567",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {
                                "body": "Sí me interesa la oportunidad"
                            }
                        }],
                        "contacts": [{
                            "wa_id": "573001234567",
                            "profile": {
                                "name": "Juan Pérez"
                            }
                        }]
                    }
                }]
            }]
        }
        
        result = await whatsapp_service.process_incoming_message(webhook_data)
        
        assert result["success"] is True
        assert result["type"] == "message"
        assert result["message_id"] == "wamid.test123"
        assert result["content"] == "Sí me interesa la oportunidad"
        assert result["context"]["interest"] == "interested"
        assert result["context"]["response_type"] == "acceptance"
    
    @pytest.mark.asyncio
    async def test_process_incoming_message_button(self, whatsapp_service):
        """Test de procesamiento de mensaje de botón entrante."""
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [{
                            "id": "wamid.test456",
                            "from": "573001234567",
                            "timestamp": "1234567890",
                            "type": "button",
                            "button": {
                                "text": "No gracias",
                                "payload": "reject"
                            }
                        }]
                    }
                }]
            }]
        }
        
        result = await whatsapp_service.process_incoming_message(webhook_data)
        
        assert result["success"] is True
        assert result["type"] == "message"
        assert result["content"] == "No gracias"
        assert result["context"]["interest"] == "not_interested"
    
    @pytest.mark.asyncio
    async def test_process_status_update(self, whatsapp_service):
        """Test de procesamiento de actualización de estado."""
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "statuses": [{
                            "id": "wamid.test789",
                            "status": "delivered",
                            "timestamp": "1234567890",
                            "recipient_id": "573001234567"
                        }]
                    }
                }]
            }]
        }
        
        result = await whatsapp_service.process_incoming_message(webhook_data)
        
        assert result["success"] is True
        assert result["type"] == "status_update"
        assert result["status"] == "delivered"
    
    @pytest.mark.asyncio
    async def test_get_templates_mock(self, mock_whatsapp_service):
        """Test de obtención de templates en modo mock."""
        templates = await mock_whatsapp_service.get_templates()
        
        assert len(templates) > 0
        assert templates[0]["status"] == "APPROVED"
        assert "name" in templates[0]
        assert "language" in templates[0]
    
    @pytest.mark.asyncio
    async def test_test_connection_mock(self, mock_whatsapp_service):
        """Test de prueba de conexión en modo mock."""
        result = await mock_whatsapp_service.test_connection()
        
        assert result["success"] is True
        assert result["mock"] is True
    
    def test_analyze_response_interested(self, whatsapp_service):
        """Test de análisis de respuesta positiva."""
        content = "Sí, me interesa mucho la oportunidad"
        result = whatsapp_service._analyze_response(content)
        
        assert result["interest"] == "interested"
        assert result["response_type"] == "acceptance"
    
    def test_analyze_response_not_interested(self, whatsapp_service):
        """Test de análisis de respuesta negativa."""
        content = "No gracias, ya tengo trabajo"
        result = whatsapp_service._analyze_response(content)
        
        assert result["interest"] == "not_interested"
        assert result["response_type"] == "rejection"
    
    def test_analyze_response_question(self, whatsapp_service):
        """Test de análisis de pregunta."""
        content = "¿Cuál es el salario?"
        result = whatsapp_service._analyze_response(content)
        
        assert result["interest"] == "interested"
        assert result["response_type"] == "question"
    
    def test_analyze_response_unknown(self, whatsapp_service):
        """Test de análisis de respuesta neutral."""
        content = "Gracias por contactarme"
        result = whatsapp_service._analyze_response(content)
        
        assert result["interest"] == "unknown"
        assert result["response_type"] == "neutral"


class TestWhatsAppServiceErrors:
    """Tests para manejo de errores en WhatsAppService."""
    
    @pytest.mark.asyncio
    async def test_send_template_not_configured(self, whatsapp_service, mock_settings):
        """Test de error cuando WhatsApp no está configurado."""
        mock_settings.WHATSAPP_ACCESS_TOKEN = None
        mock_settings.WHATSAPP_MOCK_MODE = False
        
        service = WhatsAppService()
        
        with pytest.raises(ValueError, match="WhatsApp no configurado"):
            await service.send_template_message(
                to_phone="573001234567",
                template_name="test"
            )
    
    @pytest.mark.asyncio
    async def test_process_invalid_webhook(self, whatsapp_service):
        """Test de procesamiento de webhook inválido."""
        # Webhook sin estructura esperada
        webhook_data = {"invalid": "data"}
        
        result = await whatsapp_service.process_incoming_message(webhook_data)
        
        assert result["success"] is False
        assert "error" in result
