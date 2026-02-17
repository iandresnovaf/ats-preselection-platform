"""Tests para el servicio de Comunicaciones."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4, UUID

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.communication_service import CommunicationService
from app.services.whatsapp_service import WhatsAppService
from app.models.communication import (
    Communication,
    CommunicationChannel,
    CommunicationDirection,
    CommunicationMessageType,
    CommunicationStatus,
    InterestStatus
)


@pytest_asyncio.fixture
async def mock_db():
    """Fixture para sesión de base de datos mockeada."""
    session = AsyncMock(spec=AsyncSession)
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest_asyncio.fixture
async def comm_service(mock_db):
    """Fixture para CommunicationService."""
    service = CommunicationService(mock_db)
    # Mockear el servicio de WhatsApp
    service.whatsapp_service = AsyncMock(spec=WhatsAppService)
    return service


@pytest.fixture
def sample_communication():
    """Fixture para crear una comunicación de ejemplo."""
    return Communication(
        communication_id=uuid4(),
        application_id=uuid4(),
        candidate_id=uuid4(),
        channel=CommunicationChannel.WHATSAPP,
        direction=CommunicationDirection.OUTBOUND,
        message_type=CommunicationMessageType.INITIAL,
        template_id="contacto_inicial",
        content="Template: contacto_inicial",
        recipient_phone="573001234567",
        status=CommunicationStatus.SENT,
        whatsapp_message_id="wamid.test123",
        sent_at=datetime.utcnow(),
        retry_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_failed_communication():
    """Fixture para crear una comunicación fallida."""
    return Communication(
        communication_id=uuid4(),
        application_id=uuid4(),
        candidate_id=uuid4(),
        channel=CommunicationChannel.WHATSAPP,
        direction=CommunicationDirection.OUTBOUND,
        message_type=CommunicationMessageType.INITIAL,
        template_id="contacto_inicial",
        content="Template: contacto_inicial",
        recipient_phone="573001234567",
        status=CommunicationStatus.FAILED,
        error_message="Error de red",
        retry_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestCommunicationService:
    """Tests para CommunicationService."""
    
    @pytest.mark.asyncio
    @patch('app.services.communication_service.settings')
    async def test_send_whatsapp_message_success(self, mock_settings, comm_service, mock_db):
        """Test de envío exitoso de mensaje WhatsApp."""
        mock_settings.WHATSAPP_ENABLED = True
        mock_settings.WHATSAPP_MOCK_MODE = False
        
        # Configurar mock de WhatsApp
        comm_service.whatsapp_service.send_template_message = AsyncMock(return_value={
            "success": True,
            "message_id": "wamid.test123"
        })
        
        application_id = uuid4()
        candidate_id = uuid4()
        
        result = await comm_service.send_whatsapp_message(
            application_id=application_id,
            candidate_id=candidate_id,
            to_phone="573001234567",
            template_name="contacto_inicial",
            template_variables=["Juan", "María", "Gerente"]
        )
        
        assert result.status == CommunicationStatus.SENT
        assert result.whatsapp_message_id == "wamid.test123"
        assert result.application_id == application_id
        assert result.candidate_id == candidate_id
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.services.communication_service.settings')
    async def test_send_whatsapp_message_failure(self, mock_settings, comm_service, mock_db):
        """Test de envío fallido de mensaje WhatsApp."""
        mock_settings.WHATSAPP_ENABLED = True
        mock_settings.WHATSAPP_MOCK_MODE = False
        
        # Configurar mock para retornar error
        comm_service.whatsapp_service.send_template_message = AsyncMock(return_value={
            "success": False,
            "error": "Template no encontrado",
            "error_code": 132001
        })
        
        result = await comm_service.send_whatsapp_message(
            application_id=uuid4(),
            candidate_id=uuid4(),
            to_phone="573001234567",
            template_name="template_invalido"
        )
        
        assert result.status == CommunicationStatus.FAILED
        assert result.error_message == "Template no encontrado"
        assert result.error_code == "132001"
    
    @pytest.mark.asyncio
    @patch('app.services.communication_service.settings')
    async def test_send_whatsapp_not_enabled(self, mock_settings, comm_service):
        """Test de error cuando WhatsApp no está habilitado."""
        mock_settings.WHATSAPP_ENABLED = False
        mock_settings.WHATSAPP_MOCK_MODE = False
        
        with pytest.raises(ValueError, match="WhatsApp no está habilitado"):
            await comm_service.send_whatsapp_message(
                application_id=uuid4(),
                candidate_id=uuid4(),
                to_phone="573001234567",
                template_name="contacto_inicial"
            )
    
    @pytest.mark.asyncio
    async def test_retry_failed_message_success(self, comm_service, mock_db, sample_failed_communication):
        """Test de reintento exitoso de mensaje fallido."""
        # Configurar mock de execute para retornar la comunicación fallida
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_failed_communication
        mock_db.execute.return_value = mock_result
        
        comm_service.whatsapp_service.send_template_message = AsyncMock(return_value={
            "success": True,
            "message_id": "wamid.retry123"
        })
        
        result = await comm_service.retry_failed_message(sample_failed_communication.communication_id)
        
        assert result.status == CommunicationStatus.SENT
        assert result.whatsapp_message_id == "wamid.retry123"
        assert result.retry_count == 1
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_retry_failed_message_not_found(self, comm_service, mock_db):
        """Test de reintento cuando la comunicación no existe."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(ValueError, match="Comunicación no encontrada"):
            await comm_service.retry_failed_message(uuid4())
    
    @pytest.mark.asyncio
    async def test_retry_failed_message_wrong_status(self, comm_service, mock_db, sample_communication):
        """Test de reintento cuando el estado no es FAILED."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_communication
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(ValueError, match="Solo se pueden reintentar mensajes fallidos"):
            await comm_service.retry_failed_message(sample_communication.communication_id)
    
    @pytest.mark.asyncio
    async def test_retry_failed_message_max_retries(self, comm_service, mock_db, sample_failed_communication):
        """Test de reintento cuando se alcanzó el máximo de reintentos."""
        sample_failed_communication.retry_count = 3
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_failed_communication
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(ValueError, match="Máximo de reintentos alcanzado"):
            await comm_service.retry_failed_message(sample_failed_communication.communication_id)
    
    @pytest.mark.asyncio
    @patch('app.services.communication_service.HHCandidate')
    async def test_record_inbound_message_with_candidate(self, mock_candidate_model, comm_service, mock_db):
        """Test de registro de mensaje entrante encontrando candidato."""
        # Mockear resultado de búsqueda de candidato
        mock_candidate = MagicMock()
        mock_candidate.candidate_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_candidate
        mock_db.execute.return_value = mock_result
        
        result = await comm_service.record_inbound_message(
            from_phone="573001234567",
            whatsapp_message_id="wamid.inbound123",
            content="Sí me interesa",
            interest_status="interested"
        )
        
        assert result is not None
        assert result.candidate_id == mock_candidate.candidate_id
        assert result.direction == CommunicationDirection.INBOUND
        assert result.status == CommunicationStatus.READ
        assert result.interest_status == InterestStatus.INTERESTED
        mock_db.add.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.communication_service.HHCandidate')
    async def test_record_inbound_message_no_candidate(self, mock_candidate_model, comm_service, mock_db):
        """Test de registro de mensaje entrante sin encontrar candidato."""
        # Sin candidato encontrado
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await comm_service.record_inbound_message(
            from_phone="573009999999",
            whatsapp_message_id="wamid.inbound456",
            content="Hola",
            interest_status="unknown"
        )
        
        assert result is not None
        assert result.candidate_id is None
        assert result.recipient_phone == "573009999999"
    
    @pytest.mark.asyncio
    async def test_update_message_status_to_delivered(self, comm_service, mock_db, sample_communication):
        """Test de actualización de estado a delivered."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_communication
        mock_db.execute.return_value = mock_result
        
        await comm_service.update_message_status(
            whatsapp_message_id="wamid.test123",
            status="delivered",
            timestamp="1234567890"
        )
        
        assert sample_communication.status == CommunicationStatus.DELIVERED
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_message_status_to_read(self, comm_service, mock_db, sample_communication):
        """Test de actualización de estado a read."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_communication
        mock_db.execute.return_value = mock_result
        
        await comm_service.update_message_status(
            whatsapp_message_id="wamid.test123",
            status="read",
            timestamp="1234567890"
        )
        
        assert sample_communication.status == CommunicationStatus.READ
    
    @pytest.mark.asyncio
    async def test_update_message_status_not_found(self, comm_service, mock_db):
        """Test de actualización cuando el mensaje no existe."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # No debería lanzar excepción, solo loggear warning
        await comm_service.update_message_status(
            whatsapp_message_id="wamid.notfound",
            status="delivered"
        )
    
    @pytest.mark.asyncio
    async def test_update_reply_status(self, comm_service, mock_db, sample_communication):
        """Test de actualización de estado de respuesta."""
        # Configurar mock para encontrar el mensaje padre
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_communication
        mock_db.execute.return_value = mock_result
        
        await comm_service.update_reply_status(
            from_phone="573001234567",
            reply_whatsapp_id="wamid.reply123",
            reply_content="Sí me interesa",
            interest_status="interested"
        )
        
        assert sample_communication.status == CommunicationStatus.REPLIED
        assert sample_communication.reply_whatsapp_id == "wamid.reply123"
        assert sample_communication.reply_content == "Sí me interesa"
        assert sample_communication.interest_status == InterestStatus.INTERESTED
        assert sample_communication.reply_received_at is not None
    
    @pytest.mark.asyncio
    async def test_get_communications_filtered(self, comm_service, mock_db):
        """Test de obtención de comunicaciones filtradas."""
        mock_comm1 = MagicMock(spec=Communication)
        mock_comm2 = MagicMock(spec=Communication)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_comm1, mock_comm2]
        mock_db.execute.return_value = mock_result
        
        result = await comm_service.get_communications(
            application_id=uuid4(),
            status=CommunicationStatus.SENT,
            limit=10
        )
        
        assert len(result) == 2
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_communication_by_id_found(self, comm_service, mock_db, sample_communication):
        """Test de obtención de comunicación por ID existente."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_communication
        mock_db.execute.return_value = mock_result
        
        result = await comm_service.get_communication_by_id(sample_communication.communication_id)
        
        assert result == sample_communication
    
    @pytest.mark.asyncio
    async def test_get_communication_by_id_not_found(self, comm_service, mock_db):
        """Test de obtención de comunicación por ID inexistente."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await comm_service.get_communication_by_id(uuid4())
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_pending_messages(self, comm_service, mock_db):
        """Test de obtención de mensajes pendientes."""
        mock_comm1 = MagicMock(spec=Communication)
        mock_comm2 = MagicMock(spec=Communication)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_comm1, mock_comm2]
        mock_db.execute.return_value = mock_result
        
        result = await comm_service.get_pending_messages(limit=5)
        
        assert len(result) == 2


class TestCommunicationServiceSummary:
    """Tests para funciones de resumen de CommunicationService."""
    
    @pytest.mark.asyncio
    @patch('app.services.communication_service.func')
    async def test_get_candidate_communication_summary(self, mock_func, comm_service, mock_db):
        """Test de obtención de resumen de comunicaciones."""
        candidate_id = uuid4()
        
        # Mockear conteos por estado
        mock_count_result = MagicMock()
        mock_count_result.all.return_value = [
            MagicMock(status=CommunicationStatus.SENT, count=5),
            MagicMock(status=CommunicationStatus.DELIVERED, count=3),
            MagicMock(status=CommunicationStatus.READ, count=2)
        ]
        
        # Mockear última comunicación
        mock_last_comm = MagicMock()
        mock_last_comm.created_at = datetime.utcnow()
        mock_last_comm.status = CommunicationStatus.READ
        
        mock_last_result = MagicMock()
        mock_last_result.scalar_one_or_none.return_value = mock_last_comm
        
        # Configurar side_effect para diferentes llamadas a execute
        mock_db.execute.side_effect = [mock_count_result, mock_last_result, MagicMock(scalar_one_or_none=MagicMock(return_value=None))]
        
        result = await comm_service.get_candidate_communication_summary(candidate_id)
        
        assert result["total_messages"] == 10
        assert result["has_responded"] is False
        assert "status_breakdown" in result
        assert "last_contact" in result
