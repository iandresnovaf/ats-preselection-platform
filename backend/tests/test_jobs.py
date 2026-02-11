"""Tests para el módulo de ofertas laborales (Job Openings)."""
import pytest
from datetime import datetime
from uuid import uuid4

from app.models import JobOpening, User, UserRole, UserStatus


@pytest.fixture
async def test_job_data():
    """Datos de prueba para crear una oferta."""
    return {
        "title": "Senior Software Engineer",
        "description": "We are looking for a senior developer with Python experience...",
        "department": "Engineering",
        "location": "Remote",
        "seniority": "Senior",
        "sector": "Technology",
    }


@pytest.fixture
async def test_job(db_session, test_consultant) -> JobOpening:
    """Crear una oferta de prueba."""
    job = JobOpening(
        title="Test Job",
        description="Test description",
        department="Engineering",
        location="Remote",
        seniority="Mid",
        sector="Technology",
        assigned_consultant_id=test_consultant.id,
        is_active=True,
        status="published",
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


@pytest.fixture
async def test_draft_job(db_session) -> JobOpening:
    """Crear una oferta en borrador."""
    job = JobOpening(
        title="Draft Job",
        description="Draft description",
        status="draft",
        is_active=False,
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


@pytest.mark.unit
@pytest.mark.jobs
class TestCreateJob:
    """Tests para crear ofertas laborales."""

    async def test_create_job_success(self, client, admin_headers, test_job_data, test_consultant):
        """Admin puede crear una oferta válida."""
        job_data = {
            **test_job_data,
            "assigned_consultant_id": str(test_consultant.id),
        }
        response = await client.post("/api/v1/jobs", json=job_data, headers=admin_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == test_job_data["title"]
        assert data["description"] == test_job_data["description"]
        assert data["department"] == test_job_data["department"]
        assert data["location"] == test_job_data["location"]
        assert data["seniority"] == test_job_data["seniority"]
        assert data["sector"] == test_job_data["sector"]
        assert data["assigned_consultant_id"] == str(test_consultant.id)
        assert data["is_active"] is True
        assert data["status"] == "draft"
        assert "id" in data
        assert "created_at" in data

    async def test_create_job_minimal_data(self, client, admin_headers):
        """Crear oferta con datos mínimos requeridos."""
        minimal_data = {
            "title": "Minimal Job",
            "description": "Simple description",
        }
        response = await client.post("/api/v1/jobs", json=minimal_data, headers=admin_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal Job"
        assert data["description"] == "Simple description"

    async def test_create_job_unauthorized_consultant(self, client, consultant_headers, test_job_data):
        """Consultor NO puede crear ofertas."""
        response = await client.post("/api/v1/jobs", json=test_job_data, headers=consultant_headers)
        
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    async def test_create_job_unauthorized_anonymous(self, client, test_job_data):
        """Usuario anónimo NO puede crear ofertas."""
        response = await client.post("/api/v1/jobs", json=test_job_data)
        
        assert response.status_code == 401

    async def test_create_job_invalid_data(self, client, admin_headers):
        """No se puede crear oferta con datos inválidos."""
        invalid_data = {
            "title": "",  # Título vacío no permitido
            "description": "Description",
        }
        response = await client.post("/api/v1/jobs", json=invalid_data, headers=admin_headers)
        
        assert response.status_code == 422

    async def test_create_job_missing_title(self, client, admin_headers):
        """No se puede crear oferta sin título."""
        invalid_data = {
            "description": "Description without title",
        }
        response = await client.post("/api/v1/jobs", json=invalid_data, headers=admin_headers)
        
        assert response.status_code == 422

    async def test_create_job_missing_description(self, client, admin_headers):
        """No se puede crear oferta sin descripción."""
        invalid_data = {
            "title": "Title without description",
        }
        response = await client.post("/api/v1/jobs", json=invalid_data, headers=admin_headers)
        
        assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.jobs
class TestListJobs:
    """Tests para listar ofertas laborales."""

    async def test_list_jobs_success(self, client, admin_headers, test_job):
        """Listar todas las ofertas."""
        response = await client.get("/api/v1/jobs", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_list_jobs_pagination(self, client, admin_headers, test_job):
        """Listar ofertas con paginación."""
        response = await client.get("/api/v1/jobs?skip=0&limit=1", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 1

    async def test_list_jobs_filter_by_status(self, client, admin_headers, test_job, test_draft_job):
        """Filtrar ofertas por estado."""
        response = await client.get("/api/v1/jobs?status=published", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert job["status"] == "published"

    async def test_list_jobs_filter_by_department(self, client, admin_headers, test_job):
        """Filtrar ofertas por departamento."""
        response = await client.get("/api/v1/jobs?department=Engineering", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert job["department"] == "Engineering"

    async def test_list_jobs_filter_by_location(self, client, admin_headers, test_job):
        """Filtrar ofertas por ubicación."""
        response = await client.get("/api/v1/jobs?location=Remote", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert job["location"] == "Remote"

    async def test_list_jobs_consultant_can_view(self, client, consultant_headers, test_job):
        """Consultor puede ver lista de ofertas."""
        response = await client.get("/api/v1/jobs", headers=consultant_headers)
        
        assert response.status_code == 200

    async def test_list_jobs_unauthorized(self, client):
        """Usuario anónimo NO puede listar ofertas."""
        response = await client.get("/api/v1/jobs")
        
        assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.jobs
class TestGetJob:
    """Tests para obtener una oferta específica."""

    async def test_get_job_success(self, client, admin_headers, test_job):
        """Obtener oferta por ID."""
        response = await client.get(f"/api/v1/jobs/{test_job.id}", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_job.id)
        assert data["title"] == test_job.title
        assert data["description"] == test_job.description

    async def test_get_job_not_found(self, client, admin_headers):
        """Obtener oferta inexistente devuelve 404."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/jobs/{fake_id}", headers=admin_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_job_invalid_id(self, client, admin_headers):
        """Obtener oferta con ID inválido devuelve 422."""
        response = await client.get("/api/v1/jobs/invalid-id", headers=admin_headers)
        
        assert response.status_code == 422

    async def test_get_job_consultant_can_view(self, client, consultant_headers, test_job):
        """Consultor puede ver detalle de oferta."""
        response = await client.get(f"/api/v1/jobs/{test_job.id}", headers=consultant_headers)
        
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.jobs
class TestUpdateJob:
    """Tests para actualizar ofertas laborales."""

    async def test_update_job_success(self, client, admin_headers, test_job):
        """Admin puede actualizar una oferta."""
        update_data = {
            "title": "Updated Title",
            "description": "Updated description",
            "location": "On-site",
        }
        response = await client.patch(
            f"/api/v1/jobs/{test_job.id}", 
            json=update_data, 
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated description"
        assert data["location"] == "On-site"
        # Campos no actualizados permanecen igual
        assert data["department"] == test_job.department

    async def test_update_job_partial(self, client, admin_headers, test_job):
        """Actualización parcial de oferta."""
        update_data = {
            "title": "Only Title Updated",
        }
        response = await client.patch(
            f"/api/v1/jobs/{test_job.id}", 
            json=update_data, 
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Only Title Updated"
        assert data["description"] == test_job.description  # Sin cambios

    async def test_update_job_unauthorized_consultant(self, client, consultant_headers, test_job):
        """Consultor NO puede actualizar ofertas."""
        update_data = {"title": "Hacked Title"}
        response = await client.patch(
            f"/api/v1/jobs/{test_job.id}", 
            json=update_data, 
            headers=consultant_headers
        )
        
        assert response.status_code == 403

    async def test_update_job_not_found(self, client, admin_headers):
        """Actualizar oferta inexistente devuelve 404."""
        fake_id = str(uuid4())
        update_data = {"title": "New Title"}
        response = await client.patch(
            f"/api/v1/jobs/{fake_id}", 
            json=update_data, 
            headers=admin_headers
        )
        
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.jobs
class TestDeleteJob:
    """Tests para eliminar ofertas laborales."""

    async def test_delete_job_success(self, client, admin_headers, db_session):
        """Admin puede eliminar una oferta."""
        # Crear oferta temporal
        job = JobOpening(
            title="Job to Delete",
            description="Will be deleted",
        )
        db_session.add(job)
        await db_session.flush()
        await db_session.refresh(job)
        
        response = await client.delete(f"/api/v1/jobs/{job.id}", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True

    async def test_delete_job_unauthorized_consultant(self, client, consultant_headers, test_job):
        """Consultor NO puede eliminar ofertas."""
        response = await client.delete(f"/api/v1/jobs/{test_job.id}", headers=consultant_headers)
        
        assert response.status_code == 403

    async def test_delete_job_not_found(self, client, admin_headers):
        """Eliminar oferta inexistente devuelve 404."""
        fake_id = str(uuid4())
        response = await client.delete(f"/api/v1/jobs/{fake_id}", headers=admin_headers)
        
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.jobs
class TestCloseJob:
    """Tests para cerrar ofertas laborales."""

    async def test_close_job_success(self, client, admin_headers, test_job):
        """Admin puede cerrar una oferta."""
        response = await client.post(
            f"/api/v1/jobs/{test_job.id}/close", 
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"
        assert data["is_active"] is False

    async def test_close_job_unauthorized_consultant(self, client, consultant_headers, test_job):
        """Consultor NO puede cerrar ofertas."""
        response = await client.post(
            f"/api/v1/jobs/{test_job.id}/close", 
            headers=consultant_headers
        )
        
        assert response.status_code == 403

    async def test_close_job_already_closed(self, client, admin_headers, db_session):
        """Cerrar oferta ya cerrada."""
        job = JobOpening(
            title="Already Closed",
            description="Closed job",
            status="closed",
            is_active=False,
        )
        db_session.add(job)
        await db_session.flush()
        await db_session.refresh(job)
        
        response = await client.post(
            f"/api/v1/jobs/{job.id}/close", 
            headers=admin_headers
        )
        
        # Puede devolver 200 (ya está cerrada) o 400 (error)
        assert response.status_code in [200, 400]

    async def test_close_job_not_found(self, client, admin_headers):
        """Cerrar oferta inexistente devuelve 404."""
        fake_id = str(uuid4())
        response = await client.post(f"/api/v1/jobs/{fake_id}/close", headers=admin_headers)
        
        assert response.status_code == 404
