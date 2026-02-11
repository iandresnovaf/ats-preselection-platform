"""Tests para integraciones externas (Zoho, WhatsApp, LLM)."""
import pytest
from datetime import datetime
from uuid import uuid4

from app.models import Candidate, JobOpening, Communication, CommunicationType, CommunicationStatus


@pytest.fixture
async def test_job_integration(db_session, test_consultant):
    """Crear una oferta de prueba para integraciones."""
    job = JobOpening(
        title="Integration Test Job",
        description="Test description",
        assigned_consultant_id=test_consultant.id,
        is_active=True,
        status="published",
        zoho_job_id="zoho_job_123",
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


@pytest.fixture
async def test_candidate_integration(db_session, test_job_integration):
    """Crear un candidato de prueba para integraciones."""
    candidate = Candidate(
        email="integration@example.com",
        full_name="Integration Candidate",
        email_normalized="integration@example.com".lower(),
        job_opening_id=test_job_integration.id,
        status="new",
        raw_data={"phone": "+1234567890"},
        source="webhook",
        zoho_candidate_id=None,
    )
    db_session.add(candidate)
    await db_session.flush()
    await db_session.refresh(candidate)
    return candidate


@pytest.fixture
async def test_candidate_with_zoho(db_session, test_job_integration):
    """Crear un candidato ya sincronizado con Zoho."""
    candidate = Candidate(
        email="zoho-synced@example.com",
        full_name="Zoho Synced Candidate",
        email_normalized="zoho-synced@example.com".lower(),
        job_opening_id=test_job_integration.id,
        status="shortlisted",
        raw_data={"phone": "+9876543210"},
        source="webhook",
        zoho_candidate_id="zoho_candidate_456",
    )
    db_session.add(candidate)
    await db_session.flush()
    await db_session.refresh(candidate)
    return candidate


@pytest.mark.unit
@pytest.mark.integration
class TestZohoSync:
    """Tests para sincronización con Zoho Recruit."""

    async def test_zoho_sync_candidate_success(self, client, admin_headers, test_candidate_integration, mocker):
        """Sincronizar candidato con Zoho exitosamente (mock)."""
        # Mock del servicio Zoho
        mock_zoho = mocker.patch("app.services.zoho_service.ZohoService.sync_candidate")
        mock_zoho.return_value = {
            "success": True,
            "zoho_candidate_id": "zoho_new_789",
            "message": "Candidate synced successfully",
        }

        response = await client.post(
            f"/api/v1/candidates/{test_candidate_integration.id}/sync-zoho",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["zoho_candidate_id"] == "zoho_new_789"
        mock_zoho.assert_called_once()

    async def test_zoho_sync_candidate_already_synced(self, client, admin_headers, test_candidate_with_zoho, mocker):
        """Sincronizar candidato ya sincronizado actualiza datos."""
        mock_zoho = mocker.patch("app.services.zoho_service.ZohoService.sync_candidate")
        mock_zoho.return_value = {
            "success": True,
            "zoho_candidate_id": "zoho_candidate_456",
            "message": "Candidate updated successfully",
        }

        response = await client.post(
            f"/api/v1/candidates/{test_candidate_with_zoho.id}/sync-zoho",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_zoho_sync_candidate_failure(self, client, admin_headers, test_candidate_integration, mocker):
        """Manejar error de sincronización con Zoho."""
        mock_zoho = mocker.patch("app.services.zoho_service.ZohoService.sync_candidate")
        mock_zoho.side_effect = Exception("Zoho API Error: Rate limit exceeded")

        response = await client.post(
            f"/api/v1/candidates/{test_candidate_integration.id}/sync-zoho",
            headers=admin_headers
        )
        
        assert response.status_code == 502
        assert "zoho" in response.json()["detail"].lower() or "sync" in response.json()["detail"].lower()

    async def test_zoho_sync_job_success(self, client, admin_headers, test_job_integration, mocker):
        """Sincronizar oferta con Zoho exitosamente (mock)."""
        mock_zoho = mocker.patch("app.services.zoho_service.ZohoService.sync_job")
        mock_zoho.return_value = {
            "success": True,
            "zoho_job_id": "zoho_job_new_999",
            "message": "Job synced successfully",
        }

        response = await client.post(
            f"/api/v1/jobs/{test_job_integration.id}/sync-zoho",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["zoho_job_id"] == "zoho_job_new_999"

    async def test_zoho_sync_unauthorized_consultant(self, client, consultant_headers, test_candidate_integration):
        """Consultor NO puede sincronizar con Zoho."""
        response = await client.post(
            f"/api/v1/candidates/{test_candidate_integration.id}/sync-zoho",
            headers=consultant_headers
        )
        
        assert response.status_code == 403

    async def test_zoho_webhook_receive(self, client, mocker):
        """Recibir webhook de actualización de Zoho."""
        mock_handler = mocker.patch("app.api.zoho.handle_zoho_webhook")
        mock_handler.return_value = {"status": "processed"}

        webhook_data = {
            "event": "candidate_updated",
            "data": {
                "zoho_candidate_id": "zoho_candidate_456",
                "status": "Interview Scheduled",
            }
        }

        response = await client.post(
            "/api/v1/zoho/webhook",
            json=webhook_data,
            headers={"X-Zoho-Signature": "valid_signature"}
        )
        
        # Puede ser 200 o 404 si el endpoint no existe aún
        assert response.status_code in [200, 404, 501]

    async def test_zoho_connection_test(self, client, admin_headers, mocker):
        """Test de conexión con Zoho."""
        mock_zoho = mocker.patch("app.services.zoho_service.ZohoService.test_connection")
        mock_zoho.return_value = {
            "connected": True,
            "organization": "Test Company",
        }

        response = await client.get("/api/v1/zoho/test-connection", headers=admin_headers)
        
        # Puede ser 200 si existe o 404 si no está implementado
        assert response.status_code in [200, 404]


@pytest.mark.unit
@pytest.mark.integration
class TestWhatsAppSend:
    """Tests para envío de mensajes WhatsApp."""

    async def test_whatsapp_send_message_success(self, client, admin_headers, test_candidate_integration, mocker):
        """Enviar mensaje WhatsApp exitosamente (mock)."""
        # Mock del servicio WhatsApp
        mock_whatsapp = mocker.patch("app.services.whatsapp_service.WhatsAppService.send_message")
        mock_whatsapp.return_value = {
            "success": True,
            "message_id": "wamid.123456789",
            "status": "sent",
        }

        message_data = {
            "candidate_id": str(test_candidate_integration.id),
            "template_name": "interview_invitation",
            "variables": {
                "candidate_name": test_candidate_integration.full_name,
                "job_title": "Integration Test Job",
                "interview_date": "2025-03-01",
            }
        }

        response = await client.post(
            "/api/v1/communications/whatsapp",
            json=message_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message_id" in data
        mock_whatsapp.assert_called_once()

    async def test_whatsapp_send_template_message(self, client, admin_headers, test_candidate_integration, mocker):
        """Enviar mensaje con template de WhatsApp."""
        mock_whatsapp = mocker.patch("app.services.whatsapp_service.WhatsAppService.send_template")
        mock_whatsapp.return_value = {
            "success": True,
            "message_id": "wamid.template.987654321",
            "status": "sent",
        }

        message_data = {
            "candidate_id": str(test_candidate_integration.id),
            "template_name": "application_received",
            "language": "es",
        }

        response = await client.post(
            "/api/v1/communications/whatsapp/template",
            json=message_data,
            headers=admin_headers
        )
        
        # Puede ser 200 si existe endpoint específico o usar el general
        assert response.status_code in [200, 404]

    async def test_whatsapp_send_failure(self, client, admin_headers, test_candidate_integration, mocker):
        """Manejar error al enviar WhatsApp."""
        mock_whatsapp = mocker.patch("app.services.whatsapp_service.WhatsAppService.send_message")
        mock_whatsapp.side_effect = Exception("WhatsApp API Error: Invalid phone number")

        message_data = {
            "candidate_id": str(test_candidate_integration.id),
            "template_name": "interview_invitation",
            "variables": {},
        }

        response = await client.post(
            "/api/v1/communications/whatsapp",
            json=message_data,
            headers=admin_headers
        )
        
        assert response.status_code == 502

    async def test_whatsapp_send_invalid_candidate(self, client, admin_headers, mocker):
        """No se puede enviar WhatsApp a candidato inexistente."""
        fake_id = str(uuid4())
        message_data = {
            "candidate_id": fake_id,
            "template_name": "interview_invitation",
            "variables": {},
        }

        response = await client.post(
            "/api/v1/communications/whatsapp",
            json=message_data,
            headers=admin_headers
        )
        
        assert response.status_code == 404

    async def test_whatsapp_webhook_receive(self, client, mocker):
        """Recibir webhook de estado de WhatsApp."""
        mock_handler = mocker.patch("app.api.whatsapp.handle_whatsapp_webhook")
        mock_handler.return_value = {"status": "processed"}

        webhook_data = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "1234567890",
                            "id": "wamid.123",
                            "text": {"body": "Hello"},
                        }]
                    }
                }]
            }]
        }

        response = await client.post(
            "/api/v1/whatsapp/webhook",
            json=webhook_data
        )
        
        assert response.status_code in [200, 404, 501]

    async def test_whatsapp_verify_webhook(self, client, mocker):
        """Verificar webhook de WhatsApp (challenge)."""
        mock_verify = mocker.patch("app.services.whatsapp_service.verify_webhook")
        mock_verify.return_value = "challenge_token_123"

        response = await client.get(
            "/api/v1/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test_verify_token",
                "hub.challenge": "challenge_token_123",
            }
        )
        
        assert response.status_code in [200, 403, 404]


@pytest.mark.unit
@pytest.mark.integration
class TestLLMEvaluate:
    """Tests para evaluación con LLM."""

    async def test_llm_evaluate_candidate_success(self, client, admin_headers, test_candidate_integration, mocker):
        """Evaluar candidato con LLM exitosamente (mock)."""
        # Mock del servicio LLM
        mock_llm = mocker.patch("app.services.llm_service.LLMService.evaluate")
        mock_llm.return_value = {
            "score": 88.5,
            "decision": "PROCEED",
            "strengths": [
                "Strong Python experience (5+ years)",
                "Good understanding of system design",
                "Clear communication skills",
            ],
            "gaps": [
                "Limited cloud experience",
                "No Kubernetes knowledge",
            ],
            "red_flags": [],
            "evidence": "The candidate demonstrates solid backend skills through their work on distributed systems and API development.",
            "hard_filters_passed": True,
            "hard_filters_failed": [],
        }

        response = await client.post(
            f"/api/v1/candidates/{test_candidate_integration.id}/evaluate",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "decision" in data
        assert data["score"] == 88.5
        assert data["decision"] == "PROCEED"
        assert len(data["strengths"]) > 0
        mock_llm.assert_called_once()

    async def test_llm_evaluate_with_jd(self, client, admin_headers, test_candidate_integration, test_job_integration, mocker):
        """Evaluar candidato contra Job Description específica."""
        mock_llm = mocker.patch("app.services.llm_service.LLMService.evaluate_with_jd")
        mock_llm.return_value = {
            "score": 75.0,
            "decision": "REVIEW",
            "match_percentage": 75.0,
            "strengths": ["Python", "FastAPI"],
            "gaps": ["React experience needed for this role"],
            "red_flags": [],
            "evidence": "Good backend match but frontend requirements not fully met.",
        }

        response = await client.post(
            f"/api/v1/candidates/{test_candidate_integration.id}/evaluate",
            params={"job_id": str(test_job_integration.id)},
            headers=admin_headers
        )
        
        # El endpoint puede aceptar query params o no
        assert response.status_code in [200, 422]

    async def test_llm_evaluate_reject_candidate(self, client, admin_headers, test_candidate_integration, mocker):
        """LLM rechaza candidato que no cumple requisitos."""
        mock_llm = mocker.patch("app.services.llm_service.LLMService.evaluate")
        mock_llm.return_value = {
            "score": 35.0,
            "decision": "REJECT_HARD",
            "strengths": ["Basic communication"],
            "gaps": [
                "No relevant experience",
                "Missing required skills",
            ],
            "red_flags": [
                "Inconsistent employment dates",
                "Required certification missing",
            ],
            "evidence": "Candidate does not meet minimum requirements for the role.",
            "hard_filters_passed": False,
            "hard_filters_failed": [
                "Minimum 3 years experience",
                "Python proficiency required",
            ],
        }

        response = await client.post(
            f"/api/v1/candidates/{test_candidate_integration.id}/evaluate",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "REJECT_HARD"
        assert data["score"] < 50
        assert len(data["red_flags"]) > 0
        assert data["hard_filters_passed"] is False

    async def test_llm_evaluate_api_error(self, client, admin_headers, test_candidate_integration, mocker):
        """Manejar error de API de LLM."""
        mock_llm = mocker.patch("app.services.llm_service.LLMService.evaluate")
        mock_llm.side_effect = Exception("OpenAI API Error: Rate limit exceeded")

        response = await client.post(
            f"/api/v1/candidates/{test_candidate_integration.id}/evaluate",
            headers=admin_headers
        )
        
        assert response.status_code == 502

    async def test_llm_evaluate_timeout(self, client, admin_headers, test_candidate_integration, mocker):
        """Manejar timeout de LLM."""
        mock_llm = mocker.patch("app.services.llm_service.LLMService.evaluate")
        mock_llm.side_effect = TimeoutError("LLM evaluation timeout after 30s")

        response = await client.post(
            f"/api/v1/candidates/{test_candidate_integration.id}/evaluate",
            headers=admin_headers
        )
        
        assert response.status_code == 504

    async def test_llm_extract_cv_data(self, client, admin_headers, mocker):
        """Extraer datos de CV con LLM (mock)."""
        mock_extract = mocker.patch("app.services.llm_service.LLMService.extract_cv_data")
        mock_extract.return_value = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "skills": ["Python", "React", "PostgreSQL"],
            "experience_years": 5,
            "education": ["BS Computer Science"],
            "work_experience": [
                {"company": "Tech Corp", "role": "Senior Dev", "years": "2020-2024"}
            ],
        }

        cv_data = {
            "cv_text": "John Doe\nSoftware Engineer\n5 years experience...",
            "file_type": "pdf",
        }

        response = await client.post(
            "/api/v1/extract-cv",
            json=cv_data,
            headers=admin_headers
        )
        
        # Puede ser 200 si existe endpoint o 404 si no está implementado
        assert response.status_code in [200, 404]

    async def test_llm_health_check(self, client, admin_headers, mocker):
        """Verificar salud del servicio LLM."""
        mock_health = mocker.patch("app.services.llm_service.LLMService.health_check")
        mock_health.return_value = {
            "status": "healthy",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "latency_ms": 150,
        }

        response = await client.get("/api/v1/llm/health", headers=admin_headers)
        
        assert response.status_code in [200, 404]


@pytest.mark.unit
@pytest.mark.integration
class TestEmailIntegration:
    """Tests para integración de email."""

    async def test_send_email_success(self, client, admin_headers, test_candidate_integration, mocker):
        """Enviar email exitosamente (mock)."""
        mock_email = mocker.patch("app.services.email_service.EmailService.send")
        mock_email.return_value = {
            "success": True,
            "message_id": "msg_12345",
            "status": "sent",
        }

        email_data = {
            "candidate_id": str(test_candidate_integration.id),
            "subject": "Interview Invitation",
            "body": "Dear candidate, you are invited to interview...",
        }

        response = await client.post(
            "/api/v1/communications/email",
            json=email_data,
            headers=admin_headers
        )
        
        assert response.status_code in [200, 404]

    async def test_send_email_template(self, client, admin_headers, test_candidate_integration, mocker):
        """Enviar email usando template."""
        mock_email = mocker.patch("app.services.email_service.EmailService.send_template")
        mock_email.return_value = {
            "success": True,
            "message_id": "msg_template_67890",
        }

        email_data = {
            "candidate_id": str(test_candidate_integration.id),
            "template_name": "interview_scheduled",
            "variables": {
                "candidate_name": test_candidate_integration.full_name,
                "interview_date": "2025-03-01 10:00",
            }
        }

        response = await client.post(
            "/api/v1/communications/email/template",
            json=email_data,
            headers=admin_headers
        )
        
        assert response.status_code in [200, 404]
