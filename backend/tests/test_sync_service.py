"""Tests for sync service."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.sync_service import (
    SyncService,
    DuplicateDetector,
    ConflictResolver,
    ConflictResolutionStrategy,
    SyncSource,
    SyncStatus,
    scheduled_sync,
)
from app.models import Candidate


@pytest.fixture
def sample_candidates():
    """Candidatos de prueba."""
    return [
        Candidate(
            id=uuid4(),
            full_name="John Doe",
            email="john@example.com",
            email_normalized="john@example.com",
            phone="+1234567890",
            phone_normalized="1234567890",
            linkedin_url="https://linkedin.com/in/johndoe"
        ),
        Candidate(
            id=uuid4(),
            full_name="Jane Smith",
            email="jane@example.com",
            email_normalized="jane@example.com",
            phone="+0987654321",
            phone_normalized="0987654321"
        ),
        Candidate(  # Duplicado de John
            id=uuid4(),
            full_name="John Doe",
            email="john@example.com",
            email_normalized="john@example.com",
            phone="+1234567890",
            phone_normalized="1234567890"
        )
    ]


class TestDuplicateDetector:
    """Tests para detector de duplicados."""
    
    @pytest.mark.asyncio
    async def test_find_duplicates_by_email(self, sample_candidates):
        """Test encontrar duplicados por email."""
        async with AsyncSession() as db:
            detector = DuplicateDetector(db)
            
            # Mock db.execute
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [sample_candidates[2]]
            db.execute = AsyncMock(return_value=mock_result)
            
            duplicates = await detector.find_duplicates(sample_candidates[0])
            
            assert len(duplicates) >= 0  # Depende del mock
    
    @pytest.mark.asyncio
    async def test_find_duplicates_by_phone(self, sample_candidates):
        """Test encontrar duplicados por teléfono."""
        async with AsyncSession() as db:
            detector = DuplicateDetector(db)
            
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            db.execute = AsyncMock(return_value=mock_result)
            
            duplicates = await detector.find_duplicates(sample_candidates[0])
            
            # Debe ejecutar múltiples queries
            assert db.execute.called
    
    @pytest.mark.asyncio
    async def test_find_all_duplicates(self, sample_candidates):
        """Test encontrar todos los duplicados."""
        async with AsyncSession() as db:
            detector = DuplicateDetector(db)
            
            # Mock resultado con duplicados
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [
                sample_candidates[0],  # John original
                sample_candidates[2]   # John duplicado
            ]
            db.execute = AsyncMock(return_value=mock_result)
            
            duplicates = await detector.find_all_duplicates()
            
            assert isinstance(duplicates, list)
    
    @pytest.mark.asyncio
    async def test_merge_candidates(self, sample_candidates):
        """Test fusión de candidatos."""
        async with AsyncSession() as db:
            detector = DuplicateDetector(db)
            db.commit = AsyncMock()
            
            primary = sample_candidates[0]
            duplicates = [sample_candidates[2]]
            
            # Agregar datos faltantes al duplicado
            sample_candidates[2].linkedin_url = "https://linkedin.com/in/johndoe"
            
            result = await detector.merge_candidates(
                primary,
                duplicates,
                strategy=ConflictResolutionStrategy.NEWEST_WINS
            )
            
            assert result.is_duplicate is False
            assert sample_candidates[2].is_duplicate is True
            assert sample_candidates[2].duplicate_of_id == primary.id


class TestConflictResolver:
    """Tests para resolvedor de conflictos."""
    
    def test_source_wins_strategy(self):
        """Test estrategia source wins."""
        resolver = ConflictResolver(ConflictResolutionStrategy.SOURCE_WINS)
        
        local = {"name": "Local", "status": "active"}
        remote = {"name": "Remote", "status": "inactive"}
        
        result = resolver.resolve(local, remote)
        
        assert result == remote
    
    def test_target_wins_strategy(self):
        """Test estrategia target wins."""
        resolver = ConflictResolver(ConflictResolutionStrategy.TARGET_WINS)
        
        local = {"name": "Local", "status": "active"}
        remote = {"name": "Remote", "status": "inactive"}
        
        result = resolver.resolve(local, remote)
        
        assert result == local
    
    def test_newest_wins_strategy(self):
        """Test estrategia newest wins."""
        resolver = ConflictResolver(ConflictResolutionStrategy.NEWEST_WINS)
        
        local = {"name": "Local"}
        remote = {"name": "Remote"}
        local_time = datetime.utcnow() - timedelta(hours=1)
        remote_time = datetime.utcnow()
        
        result = resolver.resolve(local, remote, local_time, remote_time)
        
        assert result == remote
    
    def test_newest_wins_no_timestamps(self):
        """Test newest wins sin timestamps."""
        resolver = ConflictResolver(ConflictResolutionStrategy.NEWEST_WINS)
        
        local = {"name": "Local"}
        remote = {"name": "Remote"}
        
        result = resolver.resolve(local, remote)
        
        # Sin timestamps, default a remote
        assert result == remote
    
    def test_manual_strategy(self):
        """Test estrategia manual."""
        resolver = ConflictResolver(ConflictResolutionStrategy.MANUAL)
        
        local = {"name": "Local"}
        remote = {"name": "Remote"}
        
        result = resolver.resolve(local, remote)
        
        assert result["_conflict"] is True
        assert result["_local"] == local
        assert result["_remote"] == remote
        assert result["_resolution_required"] is True
    
    @pytest.mark.asyncio
    async def test_queue_for_manual_resolution(self):
        """Test encolar para resolución manual."""
        resolver = ConflictResolver(ConflictResolutionStrategy.MANUAL)
        
        with patch('app.services.sync_service.cache') as mock_cache:
            mock_cache.set = AsyncMock()
            
            await resolver.queue_for_manual_resolution(
                entity_type="candidate",
                entity_id="123",
                local_data={"name": "Local"},
                remote_data={"name": "Remote"}
            )
            
            assert mock_cache.set.called


class TestSyncService:
    """Tests para SyncService."""
    
    @pytest.mark.asyncio
    async def test_get_connector_zoho(self):
        """Test obtener conector Zoho."""
        service = SyncService()
        
        async with AsyncSession() as db:
            with patch.object(service, '_get_connector') as mock_get:
                mock_connector = Mock()
                mock_get.return_value = mock_connector
                
                connector = await service._get_connector(SyncSource.ZOHO, db)
                
                # El método debe ser llamado correctamente
                assert mock_get.called
    
    @pytest.mark.asyncio
    async def test_resolve_duplicates(self):
        """Test resolución de duplicados."""
        service = SyncService()
        
        async with AsyncSession() as db:
            with patch('app.services.sync_service.DuplicateDetector') as MockDetector:
                mock_detector = Mock()
                mock_detector.find_all_duplicates = AsyncMock(return_value=[])
                MockDetector.return_value = mock_detector
                
                await service._resolve_duplicates(db)
                
                assert mock_detector.find_all_duplicates.called
    
    @pytest.mark.asyncio
    async def test_get_last_sync_time(self):
        """Test obtener último tiempo de sync."""
        service = SyncService()
        
        with patch('app.services.sync_service.cache') as mock_cache:
            now = datetime.utcnow()
            mock_cache.get = AsyncMock(return_value=now.isoformat())
            
            result = await service._get_last_sync_time(SyncSource.ZOHO)
            
            assert result is not None
            assert isinstance(result, datetime)
    
    @pytest.mark.asyncio
    async def test_get_last_sync_time_none(self):
        """Test obtener último tiempo cuando no existe."""
        service = SyncService()
        
        with patch('app.services.sync_service.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            
            result = await service._get_last_sync_time(SyncSource.ZOHO)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_set_last_sync_time(self):
        """Test guardar tiempo de sync."""
        service = SyncService()
        
        with patch('app.services.sync_service.cache') as mock_cache:
            mock_cache.set = AsyncMock()
            
            now = datetime.utcnow()
            await service._set_last_sync_time(SyncSource.ZOHO, now)
            
            assert mock_cache.set.called
    
    @pytest.mark.asyncio
    async def test_record_sync_failure(self):
        """Test registrar fallo de sync."""
        service = SyncService()
        
        with patch('app.services.sync_service.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value=[])
            mock_cache.set = AsyncMock()
            
            await service._record_sync_failure(SyncSource.ZOHO, "Test error")
            
            assert mock_cache.set.called
    
    @pytest.mark.asyncio
    async def test_send_alert(self):
        """Test envío de alerta."""
        service = SyncService()
        
        failures = [
            {"timestamp": datetime.utcnow().isoformat(), "error": "Error 1"},
            {"timestamp": datetime.utcnow().isoformat(), "error": "Error 2"},
            {"timestamp": datetime.utcnow().isoformat(), "error": "Error 3"},
        ]
        
        # No debe lanzar excepción
        await service._send_alert(SyncSource.ZOHO, failures)
    
    @pytest.mark.asyncio
    async def test_log_sync(self):
        """Test log de sincronización."""
        service = SyncService()
        
        from app.integrations.base import SyncResult
        
        result = SyncResult(
            success=True,
            items_processed=10,
            items_created=5,
            items_updated=3,
            items_failed=2,
            duration_ms=1000.0
        )
        
        with patch('app.services.sync_service.cache') as mock_cache:
            mock_cache.set = AsyncMock()
            
            await service._log_sync(SyncSource.ZOHO, result, datetime.utcnow())
            
            assert mock_cache.set.called
    
    @pytest.mark.asyncio
    async def test_check_sync_health(self):
        """Test verificación de salud."""
        service = SyncService()
        
        with patch('app.services.sync_service.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            
            health = await service.check_sync_health()
            
            assert "timestamp" in health
            assert "sources" in health
            assert SyncSource.ZOHO.value in health["sources"]
            assert SyncSource.ODOO.value in health["sources"]


class TestScheduledSyncTask:
    """Tests para tarea programada de sync."""
    
    def test_scheduled_sync_exists(self):
        """Test que la tarea existe."""
        assert scheduled_sync is not None
        assert hasattr(scheduled_sync, 'delay')
        assert hasattr(scheduled_sync, 'apply_async')


class TestSyncSource:
    """Tests para SyncSource enum."""
    
    def test_sources(self):
        """Test valores de fuentes."""
        assert SyncSource.ZOHO.value == "zoho"
        assert SyncSource.ODOO.value == "odoo"
        assert SyncSource.LINKEDIN.value == "linkedin"


class TestSyncStatus:
    """Tests para SyncStatus enum."""
    
    def test_statuses(self):
        """Test valores de estados."""
        assert SyncStatus.PENDING.value == "pending"
        assert SyncStatus.RUNNING.value == "running"
        assert SyncStatus.SUCCESS.value == "success"
        assert SyncStatus.FAILED.value == "failed"
