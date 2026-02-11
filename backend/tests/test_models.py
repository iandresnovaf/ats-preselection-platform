"""
Tests for database models.
"""
import pytest
from datetime import datetime
from uuid import uuid4

from app.models import (
    User, UserRole, UserStatus,
    Configuration,
    JobOpening,
    Candidate, CandidateStatus,
    Evaluation,
    CandidateDecision,
    Communication, CommunicationType, CommunicationStatus,
    AuditLog,
)
from app.core.auth import get_password_hash


# ============== User Model Tests ==============

@pytest.mark.asyncio
class TestUserModel:
    """Tests for User model."""
    
    async def test_user_creation(self, db_session):
        """Test basic user creation."""
        user = User(
            email="testmodel@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="Test Model User",
            role=UserRole.CONSULTANT,
            status=UserStatus.ACTIVE,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "testmodel@test.com"
        assert user.created_at is not None
        assert user.updated_at is not None
    
    async def test_user_default_values(self, db_session):
        """Test user default values."""
        user = User(
            email="default@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="Default User"
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        
        assert user.role == UserRole.CONSULTANT
        assert user.status == UserStatus.PENDING
    
    async def test_user_role_enum_values(self):
        """Test user role enum values."""
        assert UserRole.SUPER_ADMIN.value == "super_admin"
        assert UserRole.CONSULTANT.value == "consultant"
    
    async def test_user_status_enum_values(self):
        """Test user status enum values."""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.PENDING.value == "pending"
    
    async def test_user_timestamps(self, db_session):
        """Test user timestamp fields."""
        user = User(
            email="timestamps@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="Timestamp User"
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        
        # Verify timestamps are recent
        now = datetime.utcnow()
        assert (now - user.created_at).total_seconds() < 60
        assert (now - user.updated_at).total_seconds() < 60


# ============== Configuration Model Tests ==============

@pytest.mark.asyncio
class TestConfigurationModel:
    """Tests for Configuration model."""
    
    async def test_configuration_creation(self, db_session, test_admin):
        """Test configuration creation."""
        config = Configuration(
            category="general",
            key="test_setting",
            value_encrypted="encrypted_value",
            is_encrypted=True,
            description="Test configuration setting",
            updated_by=test_admin.id
        )
        db_session.add(config)
        await db_session.flush()
        await db_session.refresh(config)
        
        assert config.id is not None
        assert config.category == "general"
        assert config.key == "test_setting"
        assert config.is_encrypted is True
    
    async def test_configuration_defaults(self, db_session):
        """Test configuration default values."""
        config = Configuration(
            category="general",
            key="default_test",
            value_encrypted="value"
        )
        db_session.add(config)
        await db_session.flush()
        await db_session.refresh(config)
        
        assert config.is_encrypted is True  # Default
        assert config.is_json is False       # Default
    
    async def test_configuration_unique_constraint(self, db_session):
        """Test unique constraint on category + key."""
        config1 = Configuration(
            category="general",
            key="unique_key",
            value_encrypted="value1"
        )
        db_session.add(config1)
        await db_session.flush()
        
        # Try to add duplicate
        config2 = Configuration(
            category="general",
            key="unique_key",
            value_encrypted="value2"
        )
        db_session.add(config2)
        
        # Should raise an integrity error
        with pytest.raises(Exception):
            await db_session.flush()


# ============== Job Opening Model Tests ==============

@pytest.mark.asyncio
class TestJobOpeningModel:
    """Tests for JobOpening model."""
    
    async def test_job_opening_creation(self, db_session):
        """Test job opening creation."""
        job = JobOpening(
            title="Senior Developer",
            description="Looking for a senior developer",
            department="Engineering",
            location="Remote",
            seniority="Senior",
            sector="Technology"
        )
        db_session.add(job)
        await db_session.flush()
        await db_session.refresh(job)
        
        assert job.id is not None
        assert job.title == "Senior Developer"
        assert job.is_active is True  # Default
        assert job.status == "draft"  # Default
    
    async def test_job_opening_defaults(self, db_session):
        """Test job opening default values."""
        job = JobOpening(
            title="Test Job"
        )
        db_session.add(job)
        await db_session.flush()
        await db_session.refresh(job)
        
        assert job.is_active is True
        assert job.status == "draft"
    
    async def test_job_opening_with_consultant(self, db_session, test_consultant):
        """Test job opening with assigned consultant."""
        job = JobOpening(
            title="Consultant Job",
            assigned_consultant_id=test_consultant.id
        )
        db_session.add(job)
        await db_session.flush()
        await db_session.refresh(job)
        
        assert job.assigned_consultant_id == test_consultant.id


# ============== Candidate Model Tests ==============

@pytest.mark.asyncio
class TestCandidateModel:
    """Tests for Candidate model."""
    
    async def test_candidate_creation(self, db_session):
        """Test candidate creation."""
        # First create a job
        job = JobOpening(title="Test Job")
        db_session.add(job)
        await db_session.flush()
        
        candidate = Candidate(
            email="candidate@test.com",
            phone="+1234567890",
            full_name="Test Candidate",
            job_opening_id=job.id,
            raw_data={"cv_text": "Sample CV"},
            source="manual"
        )
        db_session.add(candidate)
        await db_session.flush()
        await db_session.refresh(candidate)
        
        assert candidate.id is not None
        assert candidate.email == "candidate@test.com"
        assert candidate.status == CandidateStatus.NEW  # Default
        assert candidate.is_duplicate is False  # Default
    
    async def test_candidate_status_enum(self):
        """Test candidate status enum values."""
        assert CandidateStatus.NEW.value == "new"
        assert CandidateStatus.IN_REVIEW.value == "in_review"
        assert CandidateStatus.SHORTLISTED.value == "shortlisted"
        assert CandidateStatus.INTERVIEW.value == "interview"
        assert CandidateStatus.DISCARDED.value == "discarded"
        assert CandidateStatus.HIRED.value == "hired"
    
    async def test_candidate_with_extraction_data(self, db_session):
        """Test candidate with extracted data."""
        job = JobOpening(title="Test Job")
        db_session.add(job)
        await db_session.flush()
        
        candidate = Candidate(
            email="extracted@test.com",
            full_name="Extracted Candidate",
            job_opening_id=job.id,
            extracted_skills=["Python", "JavaScript"],
            extracted_experience=[{"company": "Tech Co", "years": 5}],
            extracted_education=[{"degree": "BS", "field": "CS"}],
            source="webhook"
        )
        db_session.add(candidate)
        await db_session.flush()
        await db_session.refresh(candidate)
        
        assert candidate.extracted_skills == ["Python", "JavaScript"]
        assert len(candidate.extracted_experience) == 1


# ============== Evaluation Model Tests ==============

@pytest.mark.asyncio
class TestEvaluationModel:
    """Tests for Evaluation model."""
    
    async def test_evaluation_creation(self, db_session):
        """Test evaluation creation."""
        # Create job and candidate
        job = JobOpening(title="Test Job")
        db_session.add(job)
        await db_session.flush()
        
        candidate = Candidate(
            email="eval@test.com",
            full_name="Eval Candidate",
            job_opening_id=job.id
        )
        db_session.add(candidate)
        await db_session.flush()
        
        evaluation = Evaluation(
            candidate_id=candidate.id,
            score=85.5,
            decision="PROCEED",
            strengths=["Leadership", "Communication"],
            gaps=["Experience with specific tech"],
            red_flags=[],
            evidence="Candidate showed strong leadership in...",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            prompt_version="v1.0",
            hard_filters_passed=True,
            evaluation_time_ms=1500
        )
        db_session.add(evaluation)
        await db_session.flush()
        await db_session.refresh(evaluation)
        
        assert evaluation.id is not None
        assert evaluation.score == 85.5
        assert evaluation.decision == "PROCEED"
        assert evaluation.hard_filters_passed is True
    
    async def test_evaluation_with_hard_filter_failure(self, db_session):
        """Test evaluation with failed hard filters."""
        job = JobOpening(title="Test Job")
        db_session.add(job)
        await db_session.flush()
        
        candidate = Candidate(
            email="filterfail@test.com",
            full_name="Filter Fail Candidate",
            job_opening_id=job.id
        )
        db_session.add(candidate)
        await db_session.flush()
        
        evaluation = Evaluation(
            candidate_id=candidate.id,
            score=30.0,
            decision="REJECT_HARD",
            hard_filters_passed=False,
            hard_filters_failed={"min_experience": "Only 1 year, required 5"},
            llm_provider="openai",
            llm_model="gpt-4o-mini"
        )
        db_session.add(evaluation)
        await db_session.flush()
        await db_session.refresh(evaluation)
        
        assert evaluation.hard_filters_passed is False
        assert evaluation.hard_filters_failed is not None


# ============== Candidate Decision Model Tests ==============

@pytest.mark.asyncio
class TestCandidateDecisionModel:
    """Tests for CandidateDecision model."""
    
    async def test_decision_creation(self, db_session, test_consultant):
        """Test candidate decision creation."""
        # Create job and candidate
        job = JobOpening(title="Test Job")
        db_session.add(job)
        await db_session.flush()
        
        candidate = Candidate(
            email="decision@test.com",
            full_name="Decision Candidate",
            job_opening_id=job.id
        )
        db_session.add(candidate)
        await db_session.flush()
        
        decision = CandidateDecision(
            candidate_id=candidate.id,
            consultant_id=test_consultant.id,
            decision="CONTINUE",
            notes="Good candidate, proceed to interview",
            synced_to_zoho=False
        )
        db_session.add(decision)
        await db_session.flush()
        await db_session.refresh(decision)
        
        assert decision.id is not None
        assert decision.decision == "CONTINUE"
        assert decision.synced_to_zoho is False
    
    async def test_decision_synced(self, db_session, test_consultant):
        """Test synced decision."""
        job = JobOpening(title="Test Job")
        db_session.add(job)
        await db_session.flush()
        
        candidate = Candidate(
            email="synced@test.com",
            full_name="Synced Candidate",
            job_opening_id=job.id
        )
        db_session.add(candidate)
        await db_session.flush()
        
        decision = CandidateDecision(
            candidate_id=candidate.id,
            consultant_id=test_consultant.id,
            decision="DISCARD",
            synced_to_zoho=True,
            synced_at=datetime.utcnow()
        )
        db_session.add(decision)
        await db_session.flush()
        await db_session.refresh(decision)
        
        assert decision.synced_to_zoho is True
        assert decision.synced_at is not None


# ============== Communication Model Tests ==============

@pytest.mark.asyncio
class TestCommunicationModel:
    """Tests for Communication model."""
    
    async def test_communication_creation(self, db_session):
        """Test communication creation."""
        job = JobOpening(title="Test Job")
        db_session.add(job)
        await db_session.flush()
        
        candidate = Candidate(
            email="comm@test.com",
            full_name="Comm Candidate",
            job_opening_id=job.id
        )
        db_session.add(candidate)
        await db_session.flush()
        
        comm = Communication(
            candidate_id=candidate.id,
            type=CommunicationType.WHATSAPP,
            status=CommunicationStatus.PENDING,
            template_name="interview_invitation",
            subject=None,
            body="Hello, we would like to invite you...",
            retry_count=0
        )
        db_session.add(comm)
        await db_session.flush()
        await db_session.refresh(comm)
        
        assert comm.id is not None
        assert comm.type == CommunicationType.WHATSAPP
        assert comm.status == CommunicationStatus.PENDING
    
    async def test_communication_status_transitions(self, db_session):
        """Test communication status enum values."""
        assert CommunicationStatus.PENDING.value == "pending"
        assert CommunicationStatus.SENT.value == "sent"
        assert CommunicationStatus.DELIVERED.value == "delivered"
        assert CommunicationStatus.READ.value == "read"
        assert CommunicationStatus.FAILED.value == "failed"
    
    async def test_communication_email(self, db_session):
        """Test email communication."""
        job = JobOpening(title="Test Job")
        db_session.add(job)
        await db_session.flush()
        
        candidate = Candidate(
            email="emailcomm@test.com",
            full_name="Email Comm Candidate",
            job_opening_id=job.id
        )
        db_session.add(candidate)
        await db_session.flush()
        
        comm = Communication(
            candidate_id=candidate.id,
            type=CommunicationType.EMAIL,
            template_name="application_received",
            subject="Your application has been received",
            body="Dear candidate...",
            status=CommunicationStatus.SENT,
            sent_at=datetime.utcnow()
        )
        db_session.add(comm)
        await db_session.flush()
        await db_session.refresh(comm)
        
        assert comm.type == CommunicationType.EMAIL
        assert comm.status == CommunicationStatus.SENT
        assert comm.subject is not None
    
    async def test_communication_with_error(self, db_session):
        """Test communication with error."""
        job = JobOpening(title="Test Job")
        db_session.add(job)
        await db_session.flush()
        
        candidate = Candidate(
            email="error@test.com",
            full_name="Error Candidate",
            job_opening_id=job.id
        )
        db_session.add(candidate)
        await db_session.flush()
        
        comm = Communication(
            candidate_id=candidate.id,
            type=CommunicationType.WHATSAPP,
            status=CommunicationStatus.FAILED,
            error_message="Failed to send: Invalid phone number",
            retry_count=3
        )
        db_session.add(comm)
        await db_session.flush()
        await db_session.refresh(comm)
        
        assert comm.status == CommunicationStatus.FAILED
        assert comm.error_message is not None
        assert comm.retry_count == 3


# ============== Audit Log Model Tests ==============

@pytest.mark.asyncio
class TestAuditLogModel:
    """Tests for AuditLog model."""
    
    async def test_audit_log_creation(self, db_session, test_admin):
        """Test audit log creation."""
        log = AuditLog(
            user_id=test_admin.id,
            action="CREATE",
            entity_type="user",
            entity_id="some-uuid",
            old_values=None,
            new_values={"email": "new@example.com", "role": "consultant"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0..."
        )
        db_session.add(log)
        await db_session.flush()
        await db_session.refresh(log)
        
        assert log.id is not None
        assert log.action == "CREATE"
        assert log.entity_type == "user"
        assert log.new_values is not None
    
    async def test_audit_log_update(self, db_session, test_admin):
        """Test audit log for update action."""
        log = AuditLog(
            user_id=test_admin.id,
            action="UPDATE",
            entity_type="candidate",
            entity_id="candidate-uuid",
            old_values={"status": "new"},
            new_values={"status": "shortlisted"},
            ip_address="10.0.0.1"
        )
        db_session.add(log)
        await db_session.flush()
        await db_session.refresh(log)
        
        assert log.action == "UPDATE"
        assert log.old_values is not None
        assert log.new_values is not None
    
    async def test_audit_log_delete(self, db_session, test_admin):
        """Test audit log for delete action."""
        log = AuditLog(
            user_id=test_admin.id,
            action="DELETE",
            entity_type="job_opening",
            entity_id="job-uuid",
            old_values={"title": "Old Job"},
            new_values=None
        )
        db_session.add(log)
        await db_session.flush()
        await db_session.refresh(log)
        
        assert log.action == "DELETE"
        assert log.old_values is not None
        assert log.new_values is None
    
    async def test_audit_log_login(self, db_session, test_admin):
        """Test audit log for login action."""
        log = AuditLog(
            user_id=test_admin.id,
            action="LOGIN",
            entity_type="user",
            entity_id=str(test_admin.id),
            ip_address="192.168.1.100"
        )
        db_session.add(log)
        await db_session.flush()
        await db_session.refresh(log)
        
        assert log.action == "LOGIN"
        assert log.created_at is not None


# ============== Model Relationship Tests ==============

@pytest.mark.asyncio
class TestModelRelationships:
    """Tests for model relationships."""
    
    async def test_user_job_relationship(self, db_session, test_consultant):
        """Test user-job relationship."""
        job = JobOpening(
            title="Consultant Assigned Job",
            assigned_consultant_id=test_consultant.id
        )
        db_session.add(job)
        await db_session.flush()
        await db_session.refresh(job)
        
        # Load relationship
        await db_session.refresh(test_consultant, ['assigned_jobs'])
        assert len(test_consultant.assigned_jobs) > 0
    
    async def test_job_candidate_relationship(self, db_session):
        """Test job-candidate relationship."""
        job = JobOpening(title="Relationship Test Job")
        db_session.add(job)
        await db_session.flush()
        
        candidate = Candidate(
            email="relation@test.com",
            full_name="Relation Candidate",
            job_opening_id=job.id
        )
        db_session.add(candidate)
        await db_session.flush()
        await db_session.refresh(job, ['candidates'])
        
        assert len(job.candidates) > 0
    
    async def test_candidate_evaluation_relationship(self, db_session):
        """Test candidate-evaluation relationship."""
        job = JobOpening(title="Test Job")
        db_session.add(job)
        await db_session.flush()
        
        candidate = Candidate(
            email="evalrelation@test.com",
            full_name="Eval Relation Candidate",
            job_opening_id=job.id
        )
        db_session.add(candidate)
        await db_session.flush()
        
        evaluation = Evaluation(
            candidate_id=candidate.id,
            score=90.0,
            decision="PROCEED",
            llm_provider="openai",
            llm_model="gpt-4o-mini"
        )
        db_session.add(evaluation)
        await db_session.flush()
        await db_session.refresh(candidate, ['evaluations'])
        
        assert len(candidate.evaluations) > 0
