"""Tests para el módulo de candidatos (Candidates)."""
import pytest
from datetime import datetime
from uuid import uuid4

from app.models import Candidate, CandidateStatus, JobOpening, Evaluation


@pytest.fixture
async def test_candidate_data(test_job):
    """Datos de prueba para crear un candidato."""
    return {
        "job_opening_id": str(test_job.id),
        "raw_data": {
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "skills": ["Python", "FastAPI", "React"],
            "experience_years": 5,
        },
        "source": "manual",
    }


@pytest.fixture
async def test_job(db_session, test_consultant) -> JobOpening:
    """Crear una oferta de prueba."""
    job = JobOpening(
        title="Test Job for Candidates",
        description="Test description",
        department="Engineering",
        assigned_consultant_id=test_consultant.id,
        is_active=True,
        status="published",
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


@pytest.fixture
async def test_candidate(db_session, test_job) -> Candidate:
    """Crear un candidato de prueba."""
    candidate = Candidate(
        email="candidate@example.com",
        phone="+1234567890",
        full_name="Test Candidate",
        email_normalized="candidate@example.com".lower(),
        phone_normalized="1234567890",
        job_opening_id=test_job.id,
        status=CandidateStatus.NEW,
        raw_data={"experience": "5 years"},
        source="manual",
    )
    db_session.add(candidate)
    await db_session.flush()
    await db_session.refresh(candidate)
    return candidate


@pytest.fixture
async def test_candidate_with_evaluation(db_session, test_candidate) -> Candidate:
    """Crear un candidato con evaluación."""
    evaluation = Evaluation(
        candidate_id=test_candidate.id,
        score=85.5,
        decision="PROCEED",
        strengths=["Python", "Leadership"],
        gaps=["Kubernetes"],
        red_flags=[],
        evidence="Strong background in backend development",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        prompt_version="v1.0",
        hard_filters_passed=True,
        evaluation_time_ms=1500,
    )
    db_session.add(evaluation)
    await db_session.flush()
    await db_session.refresh(test_candidate)
    return test_candidate


@pytest.mark.unit
@pytest.mark.candidates
class TestCreateCandidate:
    """Tests para crear candidatos."""

    async def test_create_candidate_success(self, client, admin_headers, test_candidate_data):
        """Crear candidato válido."""
        response = await client.post("/api/v1/candidates", json=test_candidate_data, headers=admin_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_candidate_data["raw_data"]["email"]
        assert data["full_name"] == test_candidate_data["raw_data"]["full_name"]
        assert data["phone"] == test_candidate_data["raw_data"]["phone"]
        assert data["job_opening_id"] == test_candidate_data["job_opening_id"]
        assert data["status"] == "new"
        assert data["source"] == "manual"
        assert "id" in data

    async def test_create_candidate_consultant_can_create(self, client, consultant_headers, test_candidate_data):
        """Consultor puede crear candidatos."""
        response = await client.post("/api/v1/candidates", json=test_candidate_data, headers=consultant_headers)
        
        assert response.status_code == 201

    async def test_create_candidate_unauthorized(self, client, test_candidate_data):
        """Usuario anónimo NO puede crear candidatos."""
        response = await client.post("/api/v1/candidates", json=test_candidate_data)
        
        assert response.status_code == 401

    async def test_create_candidate_invalid_job(self, client, admin_headers, test_candidate_data):
        """No se puede crear candidato con job_id inválido."""
        test_candidate_data["job_opening_id"] = str(uuid4())
        response = await client.post("/api/v1/candidates", json=test_candidate_data, headers=admin_headers)
        
        assert response.status_code == 404

    async def test_create_candidate_missing_job_id(self, client, admin_headers):
        """No se puede crear candidato sin job_opening_id."""
        invalid_data = {
            "raw_data": {"full_name": "John"},
            "source": "manual",
        }
        response = await client.post("/api/v1/candidates", json=invalid_data, headers=admin_headers)
        
        assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.candidates
class TestListCandidates:
    """Tests para listar candidatos."""

    async def test_list_candidates_success(self, client, admin_headers, test_candidate):
        """Listar todos los candidatos."""
        response = await client.get("/api/v1/candidates", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_list_candidates_by_job(self, client, admin_headers, test_candidate, test_job):
        """Filtrar candidatos por oferta."""
        response = await client.get(f"/api/v1/candidates?job_opening_id={test_job.id}", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        for candidate in data["items"]:
            assert candidate["job_opening_id"] == str(test_job.id)

    async def test_list_candidates_by_status(self, client, admin_headers, test_candidate):
        """Filtrar candidatos por estado."""
        response = await client.get("/api/v1/candidates?status=new", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        for candidate in data["items"]:
            assert candidate["status"] == "new"

    async def test_list_candidates_search_by_name(self, client, admin_headers, test_candidate):
        """Buscar candidatos por nombre."""
        response = await client.get("/api/v1/candidates?search=Test", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        # Debería encontrar el candidato de prueba
        assert len(data["items"]) >= 1

    async def test_list_candidates_pagination(self, client, admin_headers, test_candidate):
        """Listar candidatos con paginación."""
        response = await client.get("/api/v1/candidates?skip=0&limit=10", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 10

    async def test_list_candidates_consultant_can_view(self, client, consultant_headers, test_candidate):
        """Consultor puede ver lista de candidatos."""
        response = await client.get("/api/v1/candidates", headers=consultant_headers)
        
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.candidates
class TestGetCandidate:
    """Tests para obtener un candidato específico."""

    async def test_get_candidate_success(self, client, admin_headers, test_candidate):
        """Obtener candidato por ID."""
        response = await client.get(f"/api/v1/candidates/{test_candidate.id}", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_candidate.id)
        assert data["email"] == test_candidate.email
        assert data["full_name"] == test_candidate.full_name
        assert "evaluations" in data

    async def test_get_candidate_with_evaluations(self, client, admin_headers, test_candidate_with_evaluation):
        """Obtener candidato con sus evaluaciones."""
        response = await client.get(f"/api/v1/candidates/{test_candidate_with_evaluation.id}", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "evaluations" in data
        assert len(data["evaluations"]) >= 1
        assert data["latest_score"] == 85.5
        assert data["latest_decision"] == "PROCEED"

    async def test_get_candidate_not_found(self, client, admin_headers):
        """Obtener candidato inexistente devuelve 404."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/candidates/{fake_id}", headers=admin_headers)
        
        assert response.status_code == 404

    async def test_get_candidate_consultant_can_view(self, client, consultant_headers, test_candidate):
        """Consultor puede ver detalle de candidato."""
        response = await client.get(f"/api/v1/candidates/{test_candidate.id}", headers=consultant_headers)
        
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.candidates
class TestUpdateCandidate:
    """Tests para actualizar candidatos."""

    async def test_update_candidate_success(self, client, admin_headers, test_candidate):
        """Actualizar datos del candidato."""
        update_data = {
            "full_name": "Updated Name",
            "email": "updated@example.com",
            "phone": "+9876543210",
        }
        response = await client.patch(
            f"/api/v1/candidates/{test_candidate.id}", 
            json=update_data, 
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["email"] == "updated@example.com"

    async def test_update_candidate_partial(self, client, admin_headers, test_candidate):
        """Actualización parcial de candidato."""
        update_data = {
            "full_name": "Only Name Updated",
        }
        response = await client.patch(
            f"/api/v1/candidates/{test_candidate.id}", 
            json=update_data, 
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Only Name Updated"
        assert data["email"] == test_candidate.email  # Sin cambios

    async def test_update_candidate_consultant_can_update(self, client, consultant_headers, test_candidate):
        """Consultor puede actualizar candidatos."""
        update_data = {"full_name": "Consultant Updated"}
        response = await client.patch(
            f"/api/v1/candidates/{test_candidate.id}", 
            json=update_data, 
            headers=consultant_headers
        )
        
        assert response.status_code == 200

    async def test_update_candidate_not_found(self, client, admin_headers):
        """Actualizar candidato inexistente devuelve 404."""
        fake_id = str(uuid4())
        update_data = {"full_name": "New Name"}
        response = await client.patch(
            f"/api/v1/candidates/{fake_id}", 
            json=update_data, 
            headers=admin_headers
        )
        
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.candidates
class TestEvaluateCandidate:
    """Tests para evaluar candidatos con LLM."""

    async def test_evaluate_candidate_success(self, client, admin_headers, test_candidate, mocker):
        """Evaluar candidato con LLM (mock)."""
        # Mock del servicio LLM
        mock_llm = mocker.patch("app.services.llm_service.LLMService.evaluate_candidate")
        mock_llm.return_value = {
            "score": 92.0,
            "decision": "PROCEED",
            "strengths": ["Python", "System Design"],
            "gaps": ["Frontend"],
            "red_flags": [],
            "evidence": "Strong backend skills",
        }

        response = await client.post(
            f"/api/v1/candidates/{test_candidate.id}/evaluate", 
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 92.0
        assert data["decision"] == "PROCEED"
        assert "strengths" in data
        mock_llm.assert_called_once()

    async def test_evaluate_candidate_already_evaluated(self, client, admin_headers, test_candidate_with_evaluation, mocker):
        """Re-evaluar candidato ya evaluado."""
        mock_llm = mocker.patch("app.services.llm_service.LLMService.evaluate_candidate")
        mock_llm.return_value = {
            "score": 75.0,
            "decision": "REVIEW",
            "strengths": ["Communication"],
            "gaps": ["Technical depth"],
            "red_flags": [],
            "evidence": "Good communication but limited technical depth",
        }

        response = await client.post(
            f"/api/v1/candidates/{test_candidate_with_evaluation.id}/evaluate", 
            headers=admin_headers
        )
        
        # Puede crear nueva evaluación o actualizar existente
        assert response.status_code in [200, 201]

    async def test_evaluate_candidate_not_found(self, client, admin_headers, mocker):
        """Evaluar candidato inexistente devuelve 404."""
        fake_id = str(uuid4())
        response = await client.post(f"/api/v1/candidates/{fake_id}/evaluate", headers=admin_headers)
        
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.candidates
class TestChangeCandidateStatus:
    """Tests para cambiar el estado de un candidato."""

    async def test_change_status_to_shortlisted(self, client, admin_headers, test_candidate):
        """Cambiar estado a shortlisted."""
        response = await client.patch(
            f"/api/v1/candidates/{test_candidate.id}/status", 
            json={"status": "shortlisted"},
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shortlisted"

    async def test_change_status_to_interview(self, client, admin_headers, test_candidate):
        """Cambiar estado a interview."""
        # Primero cambiar a shortlisted
        await client.patch(
            f"/api/v1/candidates/{test_candidate.id}/status", 
            json={"status": "shortlisted"},
            headers=admin_headers
        )
        
        # Luego a interview
        response = await client.patch(
            f"/api/v1/candidates/{test_candidate.id}/status", 
            json={"status": "interview"},
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "interview"

    async def test_change_status_to_hired(self, client, admin_headers, test_candidate):
        """Cambiar estado a hired."""
        response = await client.patch(
            f"/api/v1/candidates/{test_candidate.id}/status", 
            json={"status": "hired"},
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "hired"

    async def test_change_status_to_discarded(self, client, admin_headers, test_candidate):
        """Cambiar estado a discarded."""
        response = await client.patch(
            f"/api/v1/candidates/{test_candidate.id}/status", 
            json={"status": "discarded"},
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "discarded"

    async def test_change_status_invalid_status(self, client, admin_headers, test_candidate):
        """Cambiar a estado inválido devuelve error."""
        response = await client.patch(
            f"/api/v1/candidates/{test_candidate.id}/status", 
            json={"status": "invalid_status"},
            headers=admin_headers
        )
        
        assert response.status_code == 422

    async def test_change_status_consultant_can_change(self, client, consultant_headers, test_candidate):
        """Consultor puede cambiar estado."""
        response = await client.patch(
            f"/api/v1/candidates/{test_candidate.id}/status", 
            json={"status": "shortlisted"},
            headers=consultant_headers
        )
        
        assert response.status_code == 200

    async def test_change_status_not_found(self, client, admin_headers):
        """Cambiar estado de candidato inexistente devuelve 404."""
        fake_id = str(uuid4())
        response = await client.patch(
            f"/api/v1/candidates/{fake_id}/status", 
            json={"status": "shortlisted"},
            headers=admin_headers
        )
        
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.candidates
class TestCandidateWorkflow:
    """Tests para el flujo completo de candidato: new → hired."""

    async def test_complete_workflow_new_to_hired(self, client, admin_headers, db_session, test_job):
        """Flujo completo: new → in_review → shortlisted → interview → hired."""
        # 1. Crear candidato
        candidate_data = {
            "job_opening_id": str(test_job.id),
            "raw_data": {
                "full_name": "Workflow Candidate",
                "email": "workflow@example.com",
            },
            "source": "manual",
        }
        response = await client.post("/api/v1/candidates", json=candidate_data, headers=admin_headers)
        assert response.status_code == 201
        candidate_id = response.json()["id"]
        assert response.json()["status"] == "new"

        # 2. Cambiar a in_review
        response = await client.patch(
            f"/api/v1/candidates/{candidate_id}/status",
            json={"status": "in_review"},
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "in_review"

        # 3. Cambiar a shortlisted
        response = await client.patch(
            f"/api/v1/candidates/{candidate_id}/status",
            json={"status": "shortlisted"},
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "shortlisted"

        # 4. Cambiar a interview
        response = await client.patch(
            f"/api/v1/candidates/{candidate_id}/status",
            json={"status": "interview"},
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "interview"

        # 5. Cambiar a hired
        response = await client.patch(
            f"/api/v1/candidates/{candidate_id}/status",
            json={"status": "hired"},
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "hired"

        # Verificar estado final
        response = await client.get(f"/api/v1/candidates/{candidate_id}", headers=admin_headers)
        assert response.json()["status"] == "hired"

    async def test_workflow_new_to_discarded(self, client, admin_headers, db_session, test_job):
        """Flujo: new → discarded."""
        # Crear candidato
        candidate_data = {
            "job_opening_id": str(test_job.id),
            "raw_data": {
                "full_name": "Discarded Candidate",
                "email": "discarded@example.com",
            },
            "source": "manual",
        }
        response = await client.post("/api/v1/candidates", json=candidate_data, headers=admin_headers)
        candidate_id = response.json()["id"]

        # Descartar
        response = await client.patch(
            f"/api/v1/candidates/{candidate_id}/status",
            json={"status": "discarded"},
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "discarded"
