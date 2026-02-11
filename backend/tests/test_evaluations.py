"""Tests para el módulo de evaluaciones (Evaluations)."""
import pytest
from datetime import datetime
from uuid import uuid4

from app.models import Evaluation, Candidate, JobOpening, CandidateStatus


@pytest.fixture
async def test_job_for_eval(db_session, test_consultant):
    """Crear una oferta de prueba para evaluaciones."""
    job = JobOpening(
        title="Job for Evaluations",
        description="Test description",
        assigned_consultant_id=test_consultant.id,
        is_active=True,
        status="published",
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


@pytest.fixture
async def test_candidate_for_eval(db_session, test_job_for_eval):
    """Crear un candidato de prueba para evaluaciones."""
    candidate = Candidate(
        email="eval-candidate@example.com",
        full_name="Evaluation Candidate",
        email_normalized="eval-candidate@example.com".lower(),
        job_opening_id=test_job_for_eval.id,
        status=CandidateStatus.NEW,
        raw_data={"skills": ["Python", "React"]},
        source="manual",
    )
    db_session.add(candidate)
    await db_session.flush()
    await db_session.refresh(candidate)
    return candidate


@pytest.fixture
async def test_evaluation(db_session, test_candidate_for_eval):
    """Crear una evaluación de prueba."""
    evaluation = Evaluation(
        candidate_id=test_candidate_for_eval.id,
        score=85.5,
        decision="PROCEED",
        strengths=["Python", "System Design", "Communication"],
        gaps=["DevOps", "Cloud"],
        red_flags=[],
        evidence="Candidate has strong backend skills demonstrated in previous projects.",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        prompt_version="v1.0",
        hard_filters_passed=True,
        hard_filters_failed=[],
        evaluation_time_ms=2450,
    )
    db_session.add(evaluation)
    await db_session.flush()
    await db_session.refresh(evaluation)
    return evaluation


@pytest.fixture
async def test_evaluation_reject(db_session, test_candidate_for_eval):
    """Crear una evaluación con decisión REJECT."""
    evaluation = Evaluation(
        candidate_id=test_candidate_for_eval.id,
        score=35.0,
        decision="REJECT_HARD",
        strengths=["Communication"],
        gaps=["Technical skills", "Experience"],
        red_flags=["Inconsistent dates", "Missing required certification"],
        evidence="Does not meet minimum requirements.",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        prompt_version="v1.0",
        hard_filters_passed=False,
        hard_filters_failed=["Minimum years of experience", "Required certification"],
        evaluation_time_ms=1800,
    )
    db_session.add(evaluation)
    await db_session.flush()
    await db_session.refresh(evaluation)
    return evaluation


@pytest.mark.unit
@pytest.mark.evaluations
class TestCreateEvaluation:
    """Tests para crear evaluaciones."""

    async def test_create_evaluation_success(self, client, admin_headers, test_candidate_for_eval, mocker):
        """Crear evaluación exitosamente."""
        # Mock del servicio LLM
        mock_llm = mocker.patch("app.services.llm_service.LLMService.evaluate_candidate")
        mock_llm.return_value = {
            "score": 78.5,
            "decision": "REVIEW",
            "strengths": ["JavaScript", "Teamwork"],
            "gaps": ["Architecture"],
            "red_flags": [],
            "evidence": "Good frontend skills, needs more backend experience.",
        }

        response = await client.post(
            f"/api/v1/candidates/{test_candidate_for_eval.id}/evaluate",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "decision" in data
        assert data["decision"] == "REVIEW"
        assert "strengths" in data
        assert "gaps" in data
        assert "llm_provider" in data
        assert "llm_model" in data
        assert "created_at" in data

    async def test_create_evaluation_manual(self, client, admin_headers, test_candidate_for_eval):
        """Crear evaluación manualmente sin LLM."""
        eval_data = {
            "candidate_id": str(test_candidate_for_eval.id),
            "score": 90.0,
            "decision": "PROCEED",
            "strengths": ["Leadership", "Architecture"],
            "gaps": ["Specific framework"],
            "red_flags": [],
            "evidence": "Excellent candidate with strong background.",
            "llm_provider": "manual",
            "llm_model": "manual",
        }
        
        response = await client.post(
            "/api/v1/evaluations",
            json=eval_data,
            headers=admin_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["score"] == 90.0
        assert data["decision"] == "PROCEED"
        assert data["llm_provider"] == "manual"

    async def test_create_evaluation_consultant_can_create(self, client, consultant_headers, test_candidate_for_eval, mocker):
        """Consultor puede crear evaluaciones."""
        mock_llm = mocker.patch("app.services.llm_service.LLMService.evaluate_candidate")
        mock_llm.return_value = {
            "score": 82.0,
            "decision": "PROCEED",
            "strengths": ["Communication"],
            "gaps": [],
            "red_flags": [],
            "evidence": "Good fit for the role.",
        }

        response = await client.post(
            f"/api/v1/candidates/{test_candidate_for_eval.id}/evaluate",
            headers=consultant_headers
        )
        
        assert response.status_code == 200

    async def test_create_evaluation_unauthorized(self, client, test_candidate_for_eval):
        """Usuario anónimo NO puede crear evaluaciones."""
        response = await client.post(
            f"/api/v1/candidates/{test_candidate_for_eval.id}/evaluate"
        )
        
        assert response.status_code == 401

    async def test_create_evaluation_invalid_candidate(self, client, admin_headers):
        """No se puede evaluar candidato inexistente."""
        fake_id = str(uuid4())
        response = await client.post(f"/api/v1/candidates/{fake_id}/evaluate", headers=admin_headers)
        
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.evaluations
class TestListEvaluations:
    """Tests para listar evaluaciones."""

    async def test_list_evaluations_by_candidate(self, client, admin_headers, test_evaluation, test_candidate_for_eval):
        """Listar evaluaciones de un candidato."""
        response = await client.get(
            f"/api/v1/candidates/{test_candidate_for_eval.id}/evaluations",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_list_evaluations_success(self, client, admin_headers, test_evaluation):
        """Listar todas las evaluaciones."""
        response = await client.get("/api/v1/evaluations", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    async def test_list_evaluations_filter_by_decision(self, client, admin_headers, test_evaluation):
        """Filtrar evaluaciones por decisión."""
        response = await client.get("/api/v1/evaluations?decision=PROCEED", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        for eval_item in data["items"]:
            assert eval_item["decision"] == "PROCEED"

    async def test_list_evaluations_filter_by_score_range(self, client, admin_headers, test_evaluation):
        """Filtrar evaluaciones por rango de score."""
        response = await client.get("/api/v1/evaluations?min_score=80&max_score=90", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        for eval_item in data["items"]:
            assert 80 <= eval_item["score"] <= 90

    async def test_list_evaluations_pagination(self, client, admin_headers, test_evaluation):
        """Listar evaluaciones con paginación."""
        response = await client.get("/api/v1/evaluations?skip=0&limit=5", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5

    async def test_list_evaluations_consultant_can_view(self, client, consultant_headers, test_evaluation):
        """Consultor puede ver lista de evaluaciones."""
        response = await client.get("/api/v1/evaluations", headers=consultant_headers)
        
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.evaluations
class TestGetEvaluation:
    """Tests para obtener una evaluación específica."""

    async def test_get_evaluation_success(self, client, admin_headers, test_evaluation):
        """Obtener evaluación por ID."""
        response = await client.get(
            f"/api/v1/evaluations/{test_evaluation.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_evaluation.id)
        assert data["score"] == test_evaluation.score
        assert data["decision"] == test_evaluation.decision
        assert data["llm_provider"] == test_evaluation.llm_provider
        assert data["llm_model"] == test_evaluation.llm_model
        assert "strengths" in data
        assert "gaps" in data

    async def test_get_evaluation_with_red_flags(self, client, admin_headers, test_evaluation_reject):
        """Obtener evaluación con red flags."""
        response = await client.get(
            f"/api/v1/evaluations/{test_evaluation_reject.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "REJECT_HARD"
        assert len(data["red_flags"]) > 0
        assert len(data["hard_filters_failed"]) > 0

    async def test_get_evaluation_not_found(self, client, admin_headers):
        """Obtener evaluación inexistente devuelve 404."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/evaluations/{fake_id}", headers=admin_headers)
        
        assert response.status_code == 404

    async def test_get_evaluation_consultant_can_view(self, client, consultant_headers, test_evaluation):
        """Consultor puede ver detalle de evaluación."""
        response = await client.get(
            f"/api/v1/evaluations/{test_evaluation.id}",
            headers=consultant_headers
        )
        
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.evaluations
class TestDeleteEvaluation:
    """Tests para eliminar evaluaciones."""

    async def test_delete_evaluation_success(self, client, admin_headers, db_session, test_candidate_for_eval):
        """Admin puede eliminar una evaluación."""
        # Crear evaluación temporal
        evaluation = Evaluation(
            candidate_id=test_candidate_for_eval.id,
            score=70.0,
            decision="REVIEW",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
        )
        db_session.add(evaluation)
        await db_session.flush()
        await db_session.refresh(evaluation)
        
        response = await client.delete(
            f"/api/v1/evaluations/{evaluation.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_delete_evaluation_unauthorized_consultant(self, client, consultant_headers, test_evaluation):
        """Consultor NO puede eliminar evaluaciones."""
        response = await client.delete(
            f"/api/v1/evaluations/{test_evaluation.id}",
            headers=consultant_headers
        )
        
        assert response.status_code == 403

    async def test_delete_evaluation_not_found(self, client, admin_headers):
        """Eliminar evaluación inexistente devuelve 404."""
        fake_id = str(uuid4())
        response = await client.delete(f"/api/v1/evaluations/{fake_id}", headers=admin_headers)
        
        assert response.status_code == 404

    async def test_delete_evaluation_unauthorized_anonymous(self, client, test_evaluation):
        """Usuario anónimo NO puede eliminar evaluaciones."""
        response = await client.delete(f"/api/v1/evaluations/{test_evaluation.id}")
        
        assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.evaluations
class TestEvaluationScoreFormatting:
    """Tests para el formateo de scores."""

    async def test_evaluation_score_decimal_format(self, client, admin_headers, test_evaluation):
        """El score se devuelve con formato decimal correcto."""
        response = await client.get(
            f"/api/v1/evaluations/{test_evaluation.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["score"], (int, float))
        # Verificar que tiene decimales si corresponde
        assert data["score"] == 85.5

    async def test_evaluation_decision_badge_colors(self, client, admin_headers, test_evaluation, test_evaluation_reject):
        """Las decisiones tienen los valores esperados para badges."""
        response1 = await client.get(
            f"/api/v1/evaluations/{test_evaluation.id}",
            headers=admin_headers
        )
        response2 = await client.get(
            f"/api/v1/evaluations/{test_evaluation_reject.id}",
            headers=admin_headers
        )
        
        assert response1.json()["decision"] == "PROCEED"  # Verde
        assert response2.json()["decision"] == "REJECT_HARD"  # Rojo

    async def test_evaluation_strengths_and_gaps_format(self, client, admin_headers, test_evaluation):
        """Strengths y gaps se devuelven como listas."""
        response = await client.get(
            f"/api/v1/evaluations/{test_evaluation.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["strengths"], list)
        assert isinstance(data["gaps"], list)
        assert len(data["strengths"]) > 0
        assert len(data["gaps"]) > 0

    async def test_evaluation_evidence_present(self, client, admin_headers, test_evaluation):
        """La evidencia se incluye en la respuesta."""
        response = await client.get(
            f"/api/v1/evaluations/{test_evaluation.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "evidence" in data
        assert len(data["evidence"]) > 0
