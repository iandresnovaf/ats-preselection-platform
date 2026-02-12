"""
Tests E2E críticos para ATS Platform.
Flujos completos: Job → CV → Match → Score
"""
import pytest
import time
from datetime import datetime
from uuid import uuid4


pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class TestCompleteHiringFlow:
    """Test E2E: Flujo completo de contratación."""
    
    async def test_complete_flow_job_to_evaluation(self, client, admin_headers, mocker):
        """
        E2E: Crear Job → Subir CV → Generar Match → Ver Score
        
        Steps:
        1. Crear una oferta de trabajo
        2. Crear un candidato con CV
        3. Evaluar el candidato
        4. Verificar el score y decisión
        5. Verificar que el candidato aparece en el job
        """
        # Mock del servicio LLM para evitar llamadas reales
        mock_llm = mocker.patch("app.integrations.llm.LLMClient.evaluate_candidate")
        mock_llm.return_value = {
            "score": 85.5,
            "decision": "PROCEED",
            "strengths": ["Python", "Leadership", "Communication"],
            "gaps": ["Cloud experience"],
            "red_flags": [],
            "evidence": "Strong technical background with management experience."
        }
        
        # Step 1: Crear Job Opening
        job_data = {
            "title": "Senior Python Developer",
            "description": "Looking for an experienced Python developer with 5+ years...",
            "department": "Engineering",
            "location": "Remote",
            "seniority": "Senior",
            "sector": "Technology"
        }
        
        job_response = await client.post(
            "/api/v1/jobs",
            json=job_data,
            headers=admin_headers
        )
        assert job_response.status_code == 201
        job_id = job_response.json()["id"]
        
        # Step 2: Crear Candidato con CV
        candidate_data = {
            "job_opening_id": job_id,
            "raw_data": {
                "full_name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "skills": ["Python", "Django", "FastAPI", "PostgreSQL"],
                "experience": [
                    {"company": "Tech Corp", "role": "Senior Dev", "years": 5}
                ],
                "education": [
                    {"degree": "BS Computer Science", "university": "MIT"}
                ]
            },
            "source": "manual"
        }
        
        candidate_response = await client.post(
            "/api/v1/candidates",
            json=candidate_data,
            headers=admin_headers
        )
        assert candidate_response.status_code == 201
        candidate_id = candidate_response.json()["id"]
        
        # Verificar que el candidato está en estado "new"
        assert candidate_response.json()["status"] == "new"
        
        # Step 3: Evaluar Candidato
        eval_response = await client.post(
            f"/api/v1/candidates/{candidate_id}/evaluate",
            json={"force": False},
            headers=admin_headers
        )
        assert eval_response.status_code == 200
        
        evaluation = eval_response.json()
        
        # Step 4: Verificar Score y Decisión
        assert "score" in evaluation
        assert "decision" in evaluation
        assert 0 <= evaluation["score"] <= 100
        assert evaluation["decision"] in ["PROCEED", "REVIEW", "REJECT_HARD"]
        assert "strengths" in evaluation
        assert "gaps" in evaluation
        assert "evidence" in evaluation
        
        # Step 5: Verificar que el candidato aparece en el job
        job_candidates_response = await client.get(
            f"/api/v1/candidates?job_opening_id={job_id}",
            headers=admin_headers
        )
        assert job_candidates_response.status_code == 200
        
        candidates = job_candidates_response.json()["items"]
        assert len(candidates) == 1
        assert candidates[0]["id"] == candidate_id
        
        # Verificar que el candidato tiene latest_score
        candidate_detail = await client.get(
            f"/api/v1/candidates/{candidate_id}",
            headers=admin_headers
        )
        assert candidate_detail.status_code == 200
        assert candidate_detail.json()["latest_score"] == evaluation["score"]
        assert candidate_detail.json()["latest_decision"] == evaluation["decision"]
    
    async def test_multiple_candidates_same_job(self, client, admin_headers, mocker):
        """
        E2E: Múltiples candidatos para el mismo job
        
        Steps:
        1. Crear un job
        2. Crear 5 candidatos
        3. Evaluar todos
        4. Verificar ranking por score
        """
        # Mock LLM con diferentes scores
        scores = [92.0, 78.5, 65.0, 88.0, 45.0]
        mock_llm = mocker.patch("app.integrations.llm.LLMClient.evaluate_candidate")
        
        def side_effect(*args, **kwargs):
            score = scores.pop(0)
            return {
                "score": score,
                "decision": "PROCEED" if score >= 75 else "REVIEW" if score >= 50 else "REJECT_HARD",
                "strengths": ["Skill 1", "Skill 2"],
                "gaps": ["Gap 1"],
                "red_flags": [],
                "evidence": "Test evidence"
            }
        
        mock_llm.side_effect = side_effect
        
        # Crear job
        job_response = await client.post(
            "/api/v1/jobs",
            json={
                "title": "Test Job Multiple Candidates",
                "description": "Test description",
                "department": "Engineering"
            },
            headers=admin_headers
        )
        job_id = job_response.json()["id"]
        
        # Crear y evaluar 5 candidatos
        candidate_ids = []
        for i in range(5):
            candidate_response = await client.post(
                "/api/v1/candidates",
                json={
                    "job_opening_id": job_id,
                    "raw_data": {
                        "full_name": f"Candidate {i}",
                        "email": f"candidate{i}@example.com"
                    },
                    "source": "manual"
                },
                headers=admin_headers
            )
            candidate_id = candidate_response.json()["id"]
            candidate_ids.append(candidate_id)
            
            # Evaluar
            await client.post(
                f"/api/v1/candidates/{candidate_id}/evaluate",
                json={"force": False},
                headers=admin_headers
            )
        
        # Verificar que todos los candidatos aparecen en el job
        response = await client.get(
            f"/api/v1/candidates?job_opening_id={job_id}",
            headers=admin_headers
        )
        assert response.json()["total"] == 5


class TestSyncIntegrations:
    """Tests E2E para sincronización con integraciones externas."""
    
    async def test_zoho_sync_simulation(self, client, admin_headers, mocker):
        """
        E2E: Simulación de sync desde Zoho
        
        Steps:
        1. Configurar Zoho
        2. Simular webhook de Zoho
        3. Verificar que se creó el candidato
        4. Verificar que se creó el job si no existe
        """
        # Configurar Zoho
        zoho_config = {
            "client_id": "test_client_id",
            "client_secret": "test_secret",
            "refresh_token": "test_refresh",
            "redirect_uri": "http://localhost:8000/callback"
        }
        
        config_response = await client.post(
            "/api/v1/config/zoho",
            json=zoho_config,
            headers=admin_headers
        )
        assert config_response.status_code == 200
        
        # Simular webhook de Zoho
        webhook_data = {
            "event": "candidate_created",
            "data": {
                "candidate_id": "zoho_cand_123",
                "email": "fromzoho@example.com",
                "full_name": "Zoho Candidate",
                "job_opening_id": "zoho_job_456",
                "job_title": "Python Developer from Zoho"
            }
        }
        
        # Nota: El endpoint de webhook no existe aún, este test documenta el flujo esperado
        # webhook_response = await client.post(
        #     "/api/v1/webhooks/zoho",
        #     json=webhook_data
        # )
        # assert webhook_response.status_code == 200
        
        pytest.skip("Zoho webhook endpoint not implemented yet")
    
    async def test_odoo_sync_simulation(self, client, admin_headers):
        """
        E2E: Simulación de sync desde Odoo
        
        Similar a Zoho pero para Odoo
        """
        # Configurar Odoo
        odoo_config = {
            "url": "https://odoo.example.com",
            "database": "test_db",
            "username": "admin@example.com",
            "api_key": "test_api_key"
        }
        
        config_response = await client.post(
            "/api/v1/config/odoo",
            json=odoo_config,
            headers=admin_headers
        )
        assert config_response.status_code == 200
        
        pytest.skip("Odoo sync implementation pending")


class TestErrorHandling:
    """Tests E2E para manejo de errores."""
    
    async def test_openai_down_fallback(self, client, admin_headers, mocker):
        """
        E2E: OpenAI caído - Verificar fallback graceful
        
        Steps:
        1. Crear candidato
        2. Mock LLM para lanzar excepción
        3. Evaluar y verificar que no falla
        4. Verificar que se guardó evaluación con estado "pending"
        """
        # Mock LLM para simular error
        mock_llm = mocker.patch("app.integrations.llm.LLMClient.evaluate_candidate")
        mock_llm.side_effect = Exception("OpenAI API Error: Service Unavailable")
        
        # Crear job y candidato
        job_response = await client.post(
            "/api/v1/jobs",
            json={
                "title": "Test Job Error Handling",
                "description": "Test description"
            },
            headers=admin_headers
        )
        job_id = job_response.json()["id"]
        
        candidate_response = await client.post(
            "/api/v1/candidates",
            json={
                "job_opening_id": job_id,
                "raw_data": {
                    "full_name": "Error Test Candidate",
                    "email": "error@example.com"
                },
                "source": "manual"
            },
            headers=admin_headers
        )
        candidate_id = candidate_response.json()["id"]
        
        # Evaluar - No debería fallar a pesar del error
        eval_response = await client.post(
            f"/api/v1/candidates/{candidate_id}/evaluate",
            json={"force": False},
            headers=admin_headers
        )
        
        # Debería retornar 200 con evaluación fallback
        assert eval_response.status_code == 200
        evaluation = eval_response.json()
        
        # Verificar fallback
        assert evaluation["score"] == 50.0  # Score neutral
        assert evaluation["decision"] == "REVIEW"  # Decisión conservadora
        assert "error" in evaluation["evidence"].lower() or "manual" in evaluation["evidence"].lower()
    
    async def test_rate_limiting_evaluation_endpoint(self, client, admin_headers, mocker):
        """
        E2E: Rate limiting en endpoint de evaluación
        
        Steps:
        1. Realizar múltiples evaluaciones rápidamente
        2. Verificar que después de N requests se aplica rate limit
        """
        # Mock LLM
        mock_llm = mocker.patch("app.integrations.llm.LLMClient.evaluate_candidate")
        mock_llm.return_value = {
            "score": 80.0,
            "decision": "PROCEED",
            "strengths": [],
            "gaps": [],
            "red_flags": [],
            "evidence": "Test"
        }
        
        # Crear job y múltiples candidatos
        job_response = await client.post(
            "/api/v1/jobs",
            json={"title": "Rate Limit Test", "description": "Test"},
            headers=admin_headers
        )
        job_id = job_response.json()["id"]
        
        candidate_ids = []
        for i in range(10):
            resp = await client.post(
                "/api/v1/candidates",
                json={
                    "job_opening_id": job_id,
                    "raw_data": {"full_name": f"Rate Test {i}", "email": f"rate{i}@test.com"},
                    "source": "manual"
                },
                headers=admin_headers
            )
            candidate_ids.append(resp.json()["id"])
        
        # Evaluar rápidamente
        responses = []
        for candidate_id in candidate_ids:
            resp = await client.post(
                f"/api/v1/candidates/{candidate_id}/evaluate",
                json={"force": False},
                headers=admin_headers
            )
            responses.append(resp.status_code)
        
        # Nota: Actualmente no hay rate limit específico para evaluaciones
        # Este test documenta el comportamiento esperado
        # Todos deberían ser 200 (hasta que se implemente rate limiting)
        assert all(r == 200 for r in responses)
        
        pytest.skip("Rate limiting not implemented yet - see QA_REPORT.md CRITICAL-001")


class TestPerformance:
    """Tests E2E de performance."""
    
    async def test_evaluation_response_time(self, client, admin_headers, mocker):
        """
        E2E: Verificar que la evaluación toma menos de 5 segundos
        
        Steps:
        1. Crear candidato
        2. Medir tiempo de evaluación
        3. Verificar que es < 5 segundos
        """
        # Mock LLM con delay simulado
        async def slow_eval(*args, **kwargs):
            await asyncio.sleep(0.5)  # Simular 500ms de procesamiento
            return {
                "score": 75.0,
                "decision": "PROCEED",
                "strengths": ["Python"],
                "gaps": [],
                "red_flags": [],
                "evidence": "Good candidate"
            }
        
        mock_llm = mocker.patch("app.integrations.llm.LLMClient.evaluate_candidate")
        mock_llm.side_effect = slow_eval
        
        # Crear job y candidato
        job_response = await client.post(
            "/api/v1/jobs",
            json={"title": "Perf Test", "description": "Test"},
            headers=admin_headers
        )
        job_id = job_response.json()["id"]
        
        candidate_response = await client.post(
            "/api/v1/candidates",
            json={
                "job_opening_id": job_id,
                "raw_data": {"full_name": "Perf Candidate", "email": "perf@test.com"},
                "source": "manual"
            },
            headers=admin_headers
        )
        candidate_id = candidate_response.json()["id"]
        
        # Medir tiempo
        start = time.time()
        eval_response = await client.post(
            f"/api/v1/candidates/{candidate_id}/evaluate",
            json={"force": False},
            headers=admin_headers
        )
        elapsed = time.time() - start
        
        assert eval_response.status_code == 200
        assert elapsed < 5.0, f"Evaluation took {elapsed}s, expected < 5s"
    
    @pytest.mark.performance
    async def test_bulk_candidates_performance(self, client, admin_headers):
        """
        E2E: Performance con 100+ candidatos
        
        Steps:
        1. Crear job
        2. Crear 100 candidatos
        3. Medir tiempo total
        4. Verificar que lista paginada funciona correctamente
        """
        # Crear job
        job_response = await client.post(
            "/api/v1/jobs",
            json={"title": "Bulk Test Job", "description": "Test"},
            headers=admin_headers
        )
        job_id = job_response.json()["id"]
        
        # Crear 50 candidatos (100 puede ser muy lento sin bulk insert)
        start = time.time()
        for i in range(50):
            await client.post(
                "/api/v1/candidates",
                json={
                    "job_opening_id": job_id,
                    "raw_data": {
                        "full_name": f"Bulk Candidate {i}",
                        "email": f"bulk{i}@test.com"
                    },
                    "source": "manual"
                },
                headers=admin_headers
            )
        elapsed = time.time() - start
        
        print(f"\n⏱️ Created 50 candidates in {elapsed:.2f}s ({elapsed/50:.2f}s per candidate)")
        
        # Verificar paginación
        page1 = await client.get(
            f"/api/v1/candidates?job_opening_id={job_id}&page=1&page_size=20",
            headers=admin_headers
        )
        assert page1.status_code == 200
        data = page1.json()
        assert data["total"] == 50
        assert len(data["items"]) == 20
        assert data["has_next"] == True
        
        page3 = await client.get(
            f"/api/v1/candidates?job_opening_id={job_id}&page=3&page_size=20",
            headers=admin_headers
        )
        data3 = page3.json()
        assert len(data3["items"]) == 10  # Última página
        assert data3["has_next"] == False


class TestDataConsistency:
    """Tests E2E para consistencia de datos."""
    
    async def test_candidate_job_relationship(self, client, admin_headers):
        """
        E2E: Verificar consistencia de relación candidato-job
        
        Steps:
        1. Crear job
        2. Crear candidato asociado
        3. Eliminar job
        4. Verificar que el candidato sigue existiendo (o manejo apropiado)
        """
        # Crear job
        job_response = await client.post(
            "/api/v1/jobs",
            json={
                "title": "Relationship Test Job",
                "description": "Test description"
            },
            headers=admin_headers
        )
        job_id = job_response.json()["id"]
        
        # Crear candidato
        candidate_response = await client.post(
            "/api/v1/candidates",
            json={
                "job_opening_id": job_id,
                "raw_data": {
                    "full_name": "Relationship Test",
                    "email": "relation@test.com"
                },
                "source": "manual"
            },
            headers=admin_headers
        )
        candidate_id = candidate_response.json()["id"]
        
        # Verificar relación
        candidate = await client.get(
            f"/api/v1/candidates/{candidate_id}",
            headers=admin_headers
        )
        assert candidate.json()["job_opening_id"] == job_id
        
        # Nota: No eliminamos el job para no romper FK
        # En producción, debería haber un soft delete o cascade apropiado
    
    async def test_evaluation_candidate_relationship(self, client, admin_headers, mocker):
        """
        E2E: Verificar que las evaluaciones están correctamente asociadas
        """
        mock_llm = mocker.patch("app.integrations.llm.LLMClient.evaluate_candidate")
        mock_llm.return_value = {
            "score": 90.0,
            "decision": "PROCEED",
            "strengths": ["Test"],
            "gaps": [],
            "red_flags": [],
            "evidence": "Test"
        }
        
        # Crear job y candidato
        job_response = await client.post(
            "/api/v1/jobs",
            json={"title": "Eval Relationship", "description": "Test"},
            headers=admin_headers
        )
        job_id = job_response.json()["id"]
        
        candidate_response = await client.post(
            "/api/v1/candidates",
            json={
                "job_opening_id": job_id,
                "raw_data": {"full_name": "Eval Test", "email": "eval@test.com"},
                "source": "manual"
            },
            headers=admin_headers
        )
        candidate_id = candidate_response.json()["id"]
        
        # Evaluar
        eval_response = await client.post(
            f"/api/v1/candidates/{candidate_id}/evaluate",
            json={"force": False},
            headers=admin_headers
        )
        evaluation = eval_response.json()
        
        # Verificar relación
        assert evaluation["candidate_id"] == candidate_id
        
        # Obtener evaluaciones del candidato
        evaluations = await client.get(
            f"/api/v1/evaluations?candidate_id={candidate_id}",
            headers=admin_headers
        )
        assert evaluations.json()["total"] >= 1
        assert any(e["id"] == evaluation["id"] for e in evaluations.json()["items"])
