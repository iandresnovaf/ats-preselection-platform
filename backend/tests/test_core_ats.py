"""
Tests unitarios para el Core ATS API.
Cobertura: Modelos, Schemas y API endpoints.
"""
import pytest
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4, UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.core_ats import (
    Candidate, Client, Role, Application, Document, Interview,
    Assessment, AssessmentScore, Flag, AuditLog,
    RoleStatus, ApplicationStage, DocumentType, AssessmentType,
    FlagSeverity, FlagSource, AuditAction
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def db_session():
    """Crear una sesión de base de datos en memoria para testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Crear tablas
    Base.metadata.create_all(bind=engine)
    
    # Crear sesión
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)


# =============================================================================
# TESTS DE MODELOS - CANDIDATES
# =============================================================================

class TestCandidateModel:
    """Tests para el modelo Candidate."""
    
    def test_create_candidate(self, db_session):
        """Test: Crear un candidato básico."""
        candidate = Candidate(
            full_name="Juan Pérez",
            email="juan@example.com",
            phone="+1234567890",
            location="Bogotá, Colombia",
            linkedin_url="https://linkedin.com/in/juanperez"
        )
        db_session.add(candidate)
        db_session.commit()
        
        assert candidate.candidate_id is not None
        assert candidate.full_name == "Juan Pérez"
        assert candidate.email == "juan@example.com"
        assert candidate.created_at is not None
        assert candidate.updated_at is not None
    
    def test_candidate_national_id_unique(self, db_session):
        """Test: El national_id debe ser único."""
        candidate1 = Candidate(
            full_name="Candidato 1",
            national_id="123456789"
        )
        db_session.add(candidate1)
        db_session.commit()
        
        # Intentar crear otro con el mismo national_id debe fallar
        candidate2 = Candidate(
            full_name="Candidato 2",
            national_id="123456789"
        )
        db_session.add(candidate2)
        
        with pytest.raises(Exception):
            db_session.commit()
    
    def test_candidate_optional_fields(self, db_session):
        """Test: Campos opcionales pueden ser NULL."""
        candidate = Candidate(
            full_name="Nombre Mínimo"
        )
        db_session.add(candidate)
        db_session.commit()
        
        assert candidate.candidate_id is not None
        assert candidate.email is None
        assert candidate.phone is None
        assert candidate.national_id is None


# =============================================================================
# TESTS DE MODELOS - CLIENTS
# =============================================================================

class TestClientModel:
    """Tests para el modelo Client."""
    
    def test_create_client(self, db_session):
        """Test: Crear un cliente."""
        client = Client(
            client_name="Empresa ABC",
            industry="Tecnología"
        )
        db_session.add(client)
        db_session.commit()
        
        assert client.client_id is not None
        assert client.client_name == "Empresa ABC"
        assert client.industry == "Tecnología"
    
    def test_client_roles_relationship(self, db_session):
        """Test: Relación cliente-roles."""
        client = Client(client_name="Empresa XYZ")
        db_session.add(client)
        db_session.commit()
        
        role = Role(
            client_id=client.client_id,
            role_title="Desarrollador Backend",
            location="Remoto"
        )
        db_session.add(role)
        db_session.commit()
        
        assert len(client.roles) == 1
        assert client.roles[0].role_title == "Desarrollador Backend"


# =============================================================================
# TESTS DE MODELOS - ROLES
# =============================================================================

class TestRoleModel:
    """Tests para el modelo Role (Vacantes)."""
    
    def test_create_role(self, db_session):
        """Test: Crear una vacante."""
        client = Client(client_name="Empresa Test")
        db_session.add(client)
        db_session.commit()
        
        role = Role(
            client_id=client.client_id,
            role_title="Senior Developer",
            location="Bogotá",
            seniority="Senior",
            status=RoleStatus.OPEN,
            date_opened=date.today()
        )
        db_session.add(role)
        db_session.commit()
        
        assert role.role_id is not None
        assert role.status == RoleStatus.OPEN
        assert role.client.client_name == "Empresa Test"
    
    def test_role_status_enum(self, db_session):
        """Test: Estados válidos de vacante."""
        client = Client(client_name="Test")
        db_session.add(client)
        db_session.commit()
        
        for status in [RoleStatus.OPEN, RoleStatus.HOLD, RoleStatus.CLOSED]:
            role = Role(
                client_id=client.client_id,
                role_title=f"Role {status.value}",
                status=status
            )
            db_session.add(role)
        
        db_session.commit()
        roles = db_session.query(Role).all()
        assert len(roles) == 3


# =============================================================================
# TESTS DE MODELOS - APPLICATIONS (ENTIDAD CENTRAL)
# =============================================================================

class TestApplicationModel:
    """Tests para el modelo Application (Entidad Central)."""
    
    def test_create_application(self, db_session):
        """Test: Crear una aplicación candidato-vacante."""
        # Setup
        client = Client(client_name="Empresa")
        db_session.add(client)
        db_session.commit()
        
        role = Role(client_id=client.client_id, role_title="Dev")
        db_session.add(role)
        db_session.commit()
        
        candidate = Candidate(full_name="Candidato")
        db_session.add(candidate)
        db_session.commit()
        
        # Crear aplicación
        application = Application(
            candidate_id=candidate.candidate_id,
            role_id=role.role_id,
            stage=ApplicationStage.SOURCING
        )
        db_session.add(application)
        db_session.commit()
        
        assert application.application_id is not None
        assert application.stage == ApplicationStage.SOURCING
        assert application.hired == False
        assert application.candidate.full_name == "Candidato"
        assert application.role.role_title == "Dev"
    
    def test_application_unique_constraint(self, db_session):
        """Test: Un candidato solo puede aplicar una vez a cada vacante."""
        client = Client(client_name="Empresa")
        db_session.add(client)
        db_session.commit()
        
        role = Role(client_id=client.client_id, role_title="Dev")
        db_session.add(role)
        db_session.commit()
        
        candidate = Candidate(full_name="Candidato")
        db_session.add(candidate)
        db_session.commit()
        
        # Primera aplicación
        app1 = Application(
            candidate_id=candidate.candidate_id,
            role_id=role.role_id
        )
        db_session.add(app1)
        db_session.commit()
        
        # Segunda aplicación (debe fallar)
        app2 = Application(
            candidate_id=candidate.candidate_id,
            role_id=role.role_id
        )
        db_session.add(app2)
        
        with pytest.raises(Exception):
            db_session.commit()
    
    def test_application_stage_progression(self, db_session):
        """Test: Progresión de etapas de la aplicación."""
        client = Client(client_name="Empresa")
        db_session.add(client)
        db_session.commit()
        
        role = Role(client_id=client.client_id, role_title="Dev")
        db_session.add(role)
        db_session.commit()
        
        candidate = Candidate(full_name="Candidato")
        db_session.add(candidate)
        db_session.commit()
        
        application = Application(
            candidate_id=candidate.candidate_id,
            role_id=role.role_id,
            stage=ApplicationStage.SOURCING
        )
        db_session.add(application)
        db_session.commit()
        
        # Avanzar etapas
        stages = [
            ApplicationStage.SHORTLIST,
            ApplicationStage.TERNA,
            ApplicationStage.INTERVIEW,
            ApplicationStage.OFFER,
            ApplicationStage.HIRED
        ]
        
        for stage in stages:
            application.stage = stage
            db_session.commit()
            assert application.stage == stage
    
    def test_application_hired_status(self, db_session):
        """Test: Marcar aplicación como contratada."""
        client = Client(client_name="Empresa")
        db_session.add(client)
        db_session.commit()
        
        role = Role(client_id=client.client_id, role_title="Dev")
        db_session.add(role)
        db_session.commit()
        
        candidate = Candidate(full_name="Candidato")
        db_session.add(candidate)
        db_session.commit()
        
        application = Application(
            candidate_id=candidate.candidate_id,
            role_id=role.role_id,
            stage=ApplicationStage.HIRED,
            hired=True,
            decision_date=date.today(),
            overall_score=Decimal("85.50")
        )
        db_session.add(application)
        db_session.commit()
        
        assert application.hired == True
        assert application.decision_date == date.today()
        assert application.overall_score == Decimal("85.50")


# =============================================================================
# TESTS DE MODELOS - DOCUMENTS
# =============================================================================

class TestDocumentModel:
    """Tests para el modelo Document."""
    
    def test_create_document(self, db_session):
        """Test: Crear un documento."""
        candidate = Candidate(full_name="Candidato")
        db_session.add(candidate)
        db_session.commit()
        
        doc = Document(
            candidate_id=candidate.candidate_id,
            doc_type=DocumentType.CV,
            original_filename="cv.pdf",
            storage_uri="/uploads/cv.pdf",
            sha256_hash="abc123",
            uploaded_by="admin@example.com"
        )
        db_session.add(doc)
        db_session.commit()
        
        assert doc.document_id is not None
        assert doc.doc_type == DocumentType.CV
        assert doc.sha256_hash == "abc123"


# =============================================================================
# TESTS DE MODELOS - INTERVIEWS
# =============================================================================

class TestInterviewModel:
    """Tests para el modelo Interview."""
    
    def test_create_interview(self, db_session):
        """Test: Crear una entrevista."""
        client = Client(client_name="Empresa")
        db_session.add(client)
        db_session.commit()
        
        role = Role(client_id=client.client_id, role_title="Dev")
        db_session.add(role)
        db_session.commit()
        
        candidate = Candidate(full_name="Candidato")
        db_session.add(candidate)
        db_session.commit()
        
        application = Application(
            candidate_id=candidate.candidate_id,
            role_id=role.role_id
        )
        db_session.add(application)
        db_session.commit()
        
        interview = Interview(
            application_id=application.application_id,
            interview_date=datetime.now(),
            interviewer="Ana García",
            summary_text="Buen candidato, experiencia sólida"
        )
        db_session.add(interview)
        db_session.commit()
        
        assert interview.interview_id is not None
        assert interview.interviewer == "Ana García"
        assert interview.application.candidate.full_name == "Candidato"


# =============================================================================
# TESTS DE MODELOS - ASSESSMENTS
# =============================================================================

class TestAssessmentModel:
    """Tests para el modelo Assessment y AssessmentScore."""
    
    def test_create_assessment(self, db_session):
        """Test: Crear una evaluación psicométrica."""
        client = Client(client_name="Empresa")
        db_session.add(client)
        db_session.commit()
        
        role = Role(client_id=client.client_id, role_title="Dev")
        db_session.add(role)
        db_session.commit()
        
        candidate = Candidate(full_name="Candidato")
        db_session.add(candidate)
        db_session.commit()
        
        application = Application(
            candidate_id=candidate.candidate_id,
            role_id=role.role_id
        )
        db_session.add(application)
        db_session.commit()
        
        assessment = Assessment(
            application_id=application.application_id,
            assessment_type=AssessmentType.FACTOR_OSCURO,
            assessment_date=date.today(),
            sincerity_score=Decimal("95.00")
        )
        db_session.add(assessment)
        db_session.commit()
        
        assert assessment.assessment_id is not None
        assert assessment.assessment_type == AssessmentType.FACTOR_OSCURO
        assert assessment.sincerity_score == Decimal("95.00")
    
    def test_create_assessment_scores(self, db_session):
        """Test: Crear scores dinámicos para una evaluación."""
        client = Client(client_name="Empresa")
        db_session.add(client)
        db_session.commit()
        
        role = Role(client_id=client.client_id, role_title="Dev")
        db_session.add(role)
        db_session.commit()
        
        candidate = Candidate(full_name="Candidato")
        db_session.add(candidate)
        db_session.commit()
        
        application = Application(
            candidate_id=candidate.candidate_id,
            role_id=role.role_id
        )
        db_session.add(application)
        db_session.commit()
        
        assessment = Assessment(
            application_id=application.application_id,
            assessment_type=AssessmentType.INTELIGENCIA_EJECUTIVA
        )
        db_session.add(assessment)
        db_session.commit()
        
        # Crear múltiples scores dinámicos
        scores = [
            AssessmentScore(assessment_id=assessment.assessment_id, dimension="planificación", value=Decimal("85.00")),
            AssessmentScore(assessment_id=assessment.assessment_id, dimension="organización", value=Decimal("90.00")),
            AssessmentScore(assessment_id=assessment.assessment_id, dimension="decisión", value=Decimal("78.50")),
        ]
        for score in scores:
            db_session.add(score)
        db_session.commit()
        
        assert len(assessment.scores) == 3
        assert assessment.scores[0].dimension == "planificación"
    
    def test_score_value_range_constraint(self, db_session):
        """Test: Los scores deben estar entre 0 y 100."""
        client = Client(client_name="Empresa")
        db_session.add(client)
        db_session.commit()
        
        role = Role(client_id=client.client_id, role_title="Dev")
        db_session.add(role)
        db_session.commit()
        
        candidate = Candidate(full_name="Candidato")
        db_session.add(candidate)
        db_session.commit()
        
        application = Application(
            candidate_id=candidate.candidate_id,
            role_id=role.role_id
        )
        db_session.add(application)
        db_session.commit()
        
        assessment = Assessment(
            application_id=application.application_id,
            assessment_type=AssessmentType.KOMPEDISC
        )
        db_session.add(assessment)
        db_session.commit()
        
        # Score fuera de rango (debe fallar)
        invalid_score = AssessmentScore(
            assessment_id=assessment.assessment_id,
            dimension="liderazgo",
            value=Decimal("150.00")  # > 100
        )
        db_session.add(invalid_score)
        
        with pytest.raises(Exception):
            db_session.commit()


# =============================================================================
# TESTS DE MODELOS - FLAGS
# =============================================================================

class TestFlagModel:
    """Tests para el modelo Flag (Riesgos/Alertas)."""
    
    def test_create_flag(self, db_session):
        """Test: Crear una alerta/flag."""
        client = Client(client_name="Empresa")
        db_session.add(client)
        db_session.commit()
        
        role = Role(client_id=client.client_id, role_title="Dev")
        db_session.add(role)
        db_session.commit()
        
        candidate = Candidate(full_name="Candidato")
        db_session.add(candidate)
        db_session.commit()
        
        application = Application(
            candidate_id=candidate.candidate_id,
            role_id=role.role_id
        )
        db_session.add(application)
        db_session.commit()
        
        flag = Flag(
            application_id=application.application_id,
            category="inconsistencia_cv",
            severity=FlagSeverity.HIGH,
            evidence="Las fechas de empleo no coinciden",
            source=FlagSource.CV
        )
        db_session.add(flag)
        db_session.commit()
        
        assert flag.flag_id is not None
        assert flag.severity == FlagSeverity.HIGH
        assert flag.source == FlagSource.CV
        assert flag.application.candidate.full_name == "Candidato"


# =============================================================================
# TESTS DE MODELOS - AUDIT LOG
# =============================================================================

class TestAuditLogModel:
    """Tests para el modelo AuditLog."""
    
    def test_create_audit_log(self, db_session):
        """Test: Crear registro de auditoría."""
        audit = AuditLog(
            entity_type="application",
            entity_id=uuid4(),
            action=AuditAction.CREATE,
            changed_by="admin@example.com",
            diff_json={"stage": {"old": None, "new": "sourcing"}}
        )
        db_session.add(audit)
        db_session.commit()
        
        assert audit.audit_id is not None
        assert audit.entity_type == "application"
        assert audit.action == AuditAction.CREATE
        assert audit.diff_json["stage"]["new"] == "sourcing"


# =============================================================================
# TESTS DE INTEGRACIÓN - FLUJO COMPLETO
# =============================================================================

class TestIntegrationFlow:
    """Tests de integración - flujo completo de contratación."""
    
    def test_full_hiring_flow(self, db_session):
        """Test: Flujo completo desde sourcing hasta hired."""
        # 1. Crear cliente
        client = Client(client_name="Tech Corp", industry="Tecnología")
        db_session.add(client)
        db_session.commit()
        
        # 2. Crear vacante
        role = Role(
            client_id=client.client_id,
            role_title="Senior Python Developer",
            location="Remoto",
            seniority="Senior",
            status=RoleStatus.OPEN,
            date_opened=date.today()
        )
        db_session.add(role)
        db_session.commit()
        
        # 3. Crear candidato
        candidate = Candidate(
            full_name="María González",
            email="maria@example.com",
            phone="+573001234567",
            national_id="1234567890"
        )
        db_session.add(candidate)
        db_session.commit()
        
        # 4. Crear aplicación
        application = Application(
            candidate_id=candidate.candidate_id,
            role_id=role.role_id,
            stage=ApplicationStage.SOURCING
        )
        db_session.add(application)
        db_session.commit()
        
        # 5. Agregar CV
        cv = Document(
            candidate_id=candidate.candidate_id,
            application_id=application.application_id,
            doc_type=DocumentType.CV,
            original_filename="maria_cv.pdf",
            storage_uri="/uploads/maria_cv.pdf",
            uploaded_by="recruiter@example.com"
        )
        db_session.add(cv)
        db_session.commit()
        
        # 6. Avanzar a shortlist
        application.stage = ApplicationStage.SHORTLIST
        db_session.commit()
        
        # 7. Entrevista
        interview = Interview(
            application_id=application.application_id,
            interview_date=datetime.now(),
            interviewer="Carlos López",
            summary_text="Excelente candidata, muy técnica"
        )
        db_session.add(interview)
        db_session.commit()
        
        # 8. Evaluación psicométrica
        assessment = Assessment(
            application_id=application.application_id,
            assessment_type=AssessmentType.INTELIGENCIA_EJECUTIVA,
            assessment_date=date.today(),
            sincerity_score=Decimal("92.00")
        )
        db_session.add(assessment)
        db_session.commit()
        
        # 9. Scores
        scores = [
            AssessmentScore(assessment_id=assessment.assessment_id, dimension="análisis", value=Decimal("88.00")),
            AssessmentScore(assessment_id=assessment.assessment_id, dimension="síntesis", value=Decimal("85.00")),
        ]
        for score in scores:
            db_session.add(score)
        db_session.commit()
        
        # 10. Avanzar etapas
        application.stage = ApplicationStage.TERNA
        db_session.commit()
        
        application.stage = ApplicationStage.INTERVIEW
        db_session.commit()
        
        application.stage = ApplicationStage.OFFER
        db_session.commit()
        
        # 11. Contratar
        application.stage = ApplicationStage.HIRED
        application.hired = True
        application.decision_date = date.today()
        application.overall_score = Decimal("87.50")
        db_session.commit()
        
        # 12. Verificar resultado
        assert application.hired == True
        assert application.stage == ApplicationStage.HIRED
        assert len(application.interviews) == 1
        assert len(application.assessments) == 1
        assert len(application.assessments[0].scores) == 2
        
        # Verificar que el candidato NO tiene scores guardados directamente
        # (los scores están en assessments -> applications)
        assert not hasattr(candidate, 'overall_score') or candidate.overall_score is None
