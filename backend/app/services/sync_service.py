"""Sync service for external integrations.

Provides:
- Scheduled sync tasks with Celery
- Duplicate detection and resolution
- Conflict resolution strategies
- Sync logging and monitoring
- Alerting on failures
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from celery import chain, group
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.database import async_session_maker
from app.integrations import (
    BaseConnector,
    ZohoRecruitConnector,
    OdooConnector,
    LinkedInConnector,
    SyncResult,
)
from app.models import Candidate, JobOpening, Configuration
from app.schemas import ZohoConfig, OdooConfig
from app.tasks import celery_app

logger = logging.getLogger(__name__)


class SyncSource(str, Enum):
    """Fuentes de sincronización."""
    ZOHO = "zoho"
    ODOO = "odoo"
    LINKEDIN = "linkedin"


class ConflictResolutionStrategy(str, Enum):
    """Estrategias para resolver conflictos."""
    SOURCE_WINS = "source_wins"      # El sistema externo tiene prioridad
    TARGET_WINS = "target_wins"      # ATS Platform tiene prioridad
    NEWEST_WINS = "newest_wins"      # El más reciente gana
    MANUAL = "manual"                # Requiere intervención manual


class SyncStatus(str, Enum):
    """Estados de sincronización."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"  # Algunos items fallaron
    FAILED = "failed"
    CANCELLED = "cancelled"


@celery_app.task(bind=True, max_retries=3)
def scheduled_sync(
    self,
    source: str,
    full_sync: bool = False,
    sync_jobs: bool = True,
    sync_candidates: bool = True
):
    """Tarea programada de sincronización.
    
    Args:
        source: Fuente de sincronización (zoho, odoo, linkedin)
        full_sync: Si True, sincroniza todo, no solo cambios recientes
        sync_jobs: Sincronizar puestos de trabajo
        sync_candidates: Sincronizar candidatos
    """
    async def run_sync():
        service = SyncService()
        result = await service.sync_from_source(
            source=SyncSource(source),
            full_sync=full_sync,
            sync_jobs=sync_jobs,
            sync_candidates=sync_candidates
        )
        return result.__dict__
    
    try:
        # Ejecutar async dentro de Celery
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(run_sync())
        return result
    except Exception as exc:
        logger.error(f"Scheduled sync failed: {exc}")
        # Reintentar con backoff
        retry_in = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=retry_in)


@celery_app.task
def check_sync_health():
    """Verificar salud de sincronizaciones y alertar si hay problemas."""
    async def check():
        service = SyncService()
        return await service.check_sync_health()
    
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(check())


@celery_app.task
def cleanup_old_sync_logs(days: int = 30):
    """Limpiar logs de sincronización antiguos.
    
    Args:
        days: Eliminar logs más antiguos que N días
    """
    # TODO: Implementar limpieza de logs
    logger.info(f"Cleaning up sync logs older than {days} days")
    return {"cleaned": 0}


class DuplicateDetector:
    """Detector de candidatos duplicados."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_duplicates(
        self,
        candidate: Candidate,
        threshold: float = 0.85
    ) -> List[Candidate]:
        """Buscar candidatos duplicados.
        
        Args:
            candidate: Candidato a verificar
            threshold: Umbral de similitud (0-1)
            
        Returns:
            Lista de posibles duplicados
        """
        duplicates = []
        
        # 1. Match exacto por email
        if candidate.email:
            result = await self.db.execute(
                select(Candidate).where(
                    and_(
                        Candidate.email_normalized == candidate.email.lower().strip(),
                        Candidate.id != candidate.id
                    )
                )
            )
            duplicates.extend(result.scalars().all())
        
        # 2. Match por teléfono normalizado
        if candidate.phone and len(candidate.phone) >= 7:
            phone_normalized = ''.join(c for c in candidate.phone if c.isdigit())
            result = await self.db.execute(
                select(Candidate).where(
                    and_(
                        Candidate.phone_normalized == phone_normalized,
                        Candidate.id != candidate.id
                    )
                )
            )
            for dup in result.scalars().all():
                if dup not in duplicates:
                    duplicates.append(dup)
        
        # 3. Match por nombre + teléfono parcial
        if candidate.full_name and candidate.phone:
            name_parts = candidate.full_name.lower().split()
            if len(name_parts) >= 2:
                phone_prefix = candidate.phone[:6]  # Primeros 6 dígitos
                result = await self.db.execute(
                    select(Candidate).where(
                        and_(
                            func.lower(Candidate.full_name).like(f"%{name_parts[0]}%"),
                            func.lower(Candidate.full_name).like(f"%{name_parts[-1]}%"),
                            Candidate.phone.like(f"{phone_prefix}%"),
                            Candidate.id != candidate.id
                        )
                    )
                )
                for dup in result.scalars().all():
                    if dup not in duplicates:
                        duplicates.append(dup)
        
        # 4. Match por nombre + LinkedIn URL
        if candidate.full_name and candidate.linkedin_url:
            linkedin_id = self._extract_linkedin_id(candidate.linkedin_url)
            if linkedin_id:
                result = await self.db.execute(
                    select(Candidate).where(
                        and_(
                            Candidate.linkedin_url.like(f"%{linkedin_id}%"),
                            Candidate.id != candidate.id
                        )
                    )
                )
                for dup in result.scalars().all():
                    if dup not in duplicates:
                        duplicates.append(dup)
        
        return duplicates
    
    async def find_all_duplicates(self) -> List[Tuple[Candidate, List[Candidate]]]:
        """Encontrar todos los duplicados en la base de datos.
        
        Returns:
            Lista de tuplas (candidato, [duplicados])
        """
        duplicates_list = []
        
        # Buscar duplicados por email
        result = await self.db.execute(
            select(Candidate).where(
                Candidate.email_normalized.in_(
                    select(Candidate.email_normalized)
                    .where(Candidate.email_normalized.isnot(None))
                    .group_by(Candidate.email_normalized)
                    .having(func.count() > 1)
                )
            ).order_by(Candidate.email_normalized)
        )
        
        by_email = {}
        for candidate in result.scalars().all():
            email = candidate.email_normalized
            if email not in by_email:
                by_email[email] = []
            by_email[email].append(candidate)
        
        for email, candidates in by_email.items():
            if len(candidates) > 1:
                # El primero es el original, el resto duplicados
                for dup in candidates[1:]:
                    duplicates_list.append((candidates[0], [dup]))
        
        return duplicates_list
    
    def _extract_linkedin_id(self, url: str) -> Optional[str]:
        """Extraer ID de LinkedIn de URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path.strip("/")
            if path.startswith("in/"):
                return path[3:]
            return None
        except Exception:
            return None
    
    async def merge_candidates(
        self,
        primary: Candidate,
        duplicates: List[Candidate],
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.NEWEST_WINS
    ) -> Candidate:
        """Fusionar candidatos duplicados.
        
        Args:
            primary: Candidato principal (conserva ID)
            duplicates: Candidatos a fusionar
            strategy: Estrategia de resolución
            
        Returns:
            Candidato fusionado
        """
        for dup in duplicates:
            # Transferir datos faltantes al primario
            if not primary.phone and dup.phone:
                primary.phone = dup.phone
                primary.phone_normalized = dup.phone_normalized
            
            if not primary.linkedin_url and dup.linkedin_url:
                primary.linkedin_url = dup.linkedin_url
            
            if not primary.extracted_skills and dup.extracted_skills:
                primary.extracted_skills = dup.extracted_skills
            
            if not primary.extracted_experience and dup.extracted_experience:
                primary.extracted_experience = dup.extracted_experience
            
            if not primary.extracted_education and dup.extracted_education:
                primary.extracted_education = dup.extracted_education
            
            # Marcar como duplicado
            dup.is_duplicate = True
            dup.duplicate_of_id = primary.id
        
        await self.db.commit()
        return primary


class SyncService:
    """Servicio de sincronización con sistemas externos."""
    
    # Alertar si fallan N sincronizaciones seguidas
    FAILURE_THRESHOLD = 3
    
    def __init__(self):
        self._connectors: Dict[SyncSource, Type[BaseConnector]] = {
            SyncSource.ZOHO: ZohoRecruitConnector,
            SyncSource.ODOO: OdooConnector,
            SyncSource.LINKEDIN: LinkedInConnector,
        }
    
    async def sync_from_source(
        self,
        source: SyncSource,
        full_sync: bool = False,
        sync_jobs: bool = True,
        sync_candidates: bool = True,
        job_opening_id: Optional[str] = None
    ) -> SyncResult:
        """Sincronizar desde una fuente externa.
        
        Args:
            source: Fuente de sincronización
            full_sync: Si True, sincroniza todo
            sync_jobs: Sincronizar puestos
            sync_candidates: Sincronizar candidatos
            job_opening_id: ID específico de job (opcional)
            
        Returns:
            Resultado de la sincronización
        """
        start_time = datetime.utcnow()
        result = SyncResult(success=True)
        
        # Obtener conector
        async with async_session_maker() as db:
            connector = await self._get_connector(source, db)
            
            if not connector:
                return SyncResult(
                    success=False,
                    errors=[f"No configuration found for {source.value}"]
                )
            
            async with connector:
                # Calcular fecha de última sincronización
                modified_since = None
                if not full_sync:
                    modified_since = await self._get_last_sync_time(source)
                
                try:
                    if sync_jobs:
                        job_result = await connector.sync_jobs(
                            modified_since=modified_since,
                            full_sync=full_sync
                        )
                        result = result.merge(job_result)
                    
                    if sync_candidates:
                        candidate_result = await connector.sync_candidates(
                            modified_since=modified_since,
                            full_sync=full_sync,
                            job_opening_id=job_opening_id
                        )
                        result = result.merge(candidate_result)
                    
                    # Detectar y resolver duplicados
                    if result.items_created > 0:
                        await self._resolve_duplicates(db)
                    
                    # Guardar timestamp de sincronización exitosa
                    if result.success:
                        await self._set_last_sync_time(source, start_time)
                    
                except Exception as e:
                    logger.error(f"Sync from {source.value} failed: {e}")
                    result.success = False
                    result.errors.append(str(e))
                    
                    # Registrar fallo para alertas
                    await self._record_sync_failure(source, str(e))
                
                # Guardar log de sincronización
                await self._log_sync(source, result, start_time)
        
        result.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return result
    
    async def _get_connector(
        self,
        source: SyncSource,
        db: AsyncSession
    ) -> Optional[BaseConnector]:
        """Obtener conector configurado."""
        from app.services.configuration_service import ConfigurationService
        
        config_service = ConfigurationService(db)
        
        if source == SyncSource.ZOHO:
            config = await config_service.get_zoho_config()
            if config:
                return ZohoRecruitConnector(db, config)
        
        elif source == SyncSource.ODOO:
            config = await config_service.get_odoo_config()
            if config:
                return OdooConnector(db, config)
        
        elif source == SyncSource.LINKEDIN:
            # LinkedIn usa configuración separada
            client_id = await config_service.get_value(
                type('C', (), {'value': 'linkedin'})(),
                "client_id"
            )
            client_secret = await config_service.get_value(
                type('C', (), {'value': 'linkedin'})(),
                "client_secret"
            )
            if client_id and client_secret:
                return LinkedInConnector(db, client_id, client_secret)
        
        return None
    
    async def _resolve_duplicates(self, db: AsyncSession):
        """Detectar y resolver duplicados después de sync."""
        detector = DuplicateDetector(db)
        duplicates = await detector.find_all_duplicates()
        
        for primary, dups in duplicates:
            await detector.merge_candidates(primary, dups)
            logger.info(f"Merged {len(dups)} duplicates into candidate {primary.id}")
    
    async def _get_last_sync_time(self, source: SyncSource) -> Optional[datetime]:
        """Obtener timestamp de última sincronización exitosa."""
        cache_key = f"sync:last:{source.value}"
        cached = await cache.get(cache_key)
        if cached:
            return datetime.fromisoformat(cached)
        return None
    
    async def _set_last_sync_time(self, source: SyncSource, sync_time: datetime):
        """Guardar timestamp de sincronización."""
        cache_key = f"sync:last:{source.value}"
        await cache.set(cache_key, sync_time.isoformat(), ttl=86400 * 30)  # 30 días
    
    async def _record_sync_failure(self, source: SyncSource, error: str):
        """Registrar fallo de sincronización."""
        cache_key = f"sync:failures:{source.value}"
        
        # Obtener contador actual
        failures = await cache.get(cache_key) or []
        if not isinstance(failures, list):
            failures = []
        
        failures.append({
            "timestamp": datetime.utcnow().isoformat(),
            "error": error
        })
        
        # Mantener solo últimos 10 fallos
        failures = failures[-10:]
        await cache.set(cache_key, failures, ttl=86400)
        
        # Alertar si supera umbral
        if len(failures) >= self.FAILURE_THRESHOLD:
            await self._send_alert(source, failures)
    
    async def _send_alert(self, source: SyncSource, failures: List[Dict]):
        """Enviar alerta de fallos consecutivos."""
        logger.error(
            f"ALERT: {source.value} sync has failed {len(failures)} times consecutively. "
            f"Last error: {failures[-1]['error']}"
        )
        
        # TODO: Enviar notificación por email/Slack
        # TODO: Guardar en tabla de alertas
    
    async def _log_sync(
        self,
        source: SyncSource,
        result: SyncResult,
        start_time: datetime
    ):
        """Guardar log de sincronización."""
        log_entry = {
            "source": source.value,
            "timestamp": datetime.utcnow().isoformat(),
            "start_time": start_time.isoformat(),
            "success": result.success,
            "items_processed": result.items_processed,
            "items_created": result.items_created,
            "items_updated": result.items_updated,
            "items_failed": result.items_failed,
            "errors": result.errors,
            "warnings": result.warnings,
            "duration_ms": result.duration_ms
        }
        
        # Guardar en cache para consulta reciente
        cache_key = f"sync:log:{source.value}:{start_time.isoformat()}"
        await cache.set(cache_key, log_entry, ttl=86400 * 7)  # 7 días
        
        # TODO: Guardar en base de datos para histórico permanente
    
    async def get_sync_logs(
        self,
        source: Optional[SyncSource] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Obtener logs de sincronización recientes.
        
        Args:
            source: Filtrar por fuente
            limit: Máximo de logs
            
        Returns:
            Lista de logs
        """
        # Buscar en cache
        pattern = f"sync:log:{source.value if source else '*'}:*"
        # Nota: Redis no soporta búsqueda por patrón directamente
        # En producción, usar una tabla de BD
        return []
    
    async def check_sync_health(self) -> Dict[str, Any]:
        """Verificar salud de sincronizaciones.
        
        Returns:
            Reporte de salud
        """
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "sources": {}
        }
        
        for source in SyncSource:
            # Verificar última sincronización
            last_sync = await self._get_last_sync_time(source)
            
            # Verificar fallos recientes
            failures = await cache.get(f"sync:failures:{source.value}") or []
            
            status = "healthy"
            if len(failures) >= self.FAILURE_THRESHOLD:
                status = "critical"
            elif len(failures) > 0:
                status = "warning"
            elif last_sync and (datetime.utcnow() - last_sync) > timedelta(hours=24):
                status = "stale"  # No se ha sincronizado en 24h
            
            health["sources"][source.value] = {
                "status": status,
                "last_sync": last_sync.isoformat() if last_sync else None,
                "recent_failures": len(failures),
                "connector_status": None
            }
        
        return health
    
    # ==================== SCHEDULING ====================
    
    def schedule_sync(
        self,
        source: SyncSource,
        interval_minutes: int = 60,
        full_sync: bool = False
    ):
        """Programar sincronización periódica.
        
        Args:
            source: Fuente de sincronización
            interval_minutes: Intervalo en minutos
            full_sync: Si True, hacer sync completo
        """
        # Usar Celery beat para scheduling
        # Esto debe configurarse en celerybeat-schedule
        logger.info(
            f"Scheduled {source.value} sync every {interval_minutes} minutes "
            f"(full_sync={full_sync})"
        )
    
    def cancel_scheduled_sync(self, source: SyncSource):
        """Cancelar sincronización programada."""
        logger.info(f"Cancelled scheduled sync for {source.value}")


class ConflictResolver:
    """Resolvedor de conflictos entre sistemas."""
    
    def __init__(
        self,
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.NEWEST_WINS
    ):
        self.strategy = strategy
    
    def resolve(
        self,
        local_data: Dict,
        remote_data: Dict,
        local_timestamp: Optional[datetime] = None,
        remote_timestamp: Optional[datetime] = None
    ) -> Dict:
        """Resolver conflicto entre datos locales y remotos.
        
        Args:
            local_data: Datos en ATS Platform
            remote_data: Datos del sistema externo
            local_timestamp: Timestamp de última modificación local
            remote_timestamp: Timestamp de última modificación remota
            
        Returns:
            Datos resueltos
        """
        if self.strategy == ConflictResolutionStrategy.SOURCE_WINS:
            return remote_data
        
        elif self.strategy == ConflictResolutionStrategy.TARGET_WINS:
            return local_data
        
        elif self.strategy == ConflictResolutionStrategy.NEWEST_WINS:
            if remote_timestamp and local_timestamp:
                if remote_timestamp > local_timestamp:
                    return remote_data
                return local_data
            # Si no hay timestamps, preferir remoto
            return remote_data
        
        elif self.strategy == ConflictResolutionStrategy.MANUAL:
            # Marcar para revisión manual
            return {
                "_conflict": True,
                "_local": local_data,
                "_remote": remote_data,
                "_resolution_required": True
            }
        
        return remote_data
    
    async def queue_for_manual_resolution(
        self,
        entity_type: str,
        entity_id: str,
        local_data: Dict,
        remote_data: Dict
    ):
        """Encolar conflicto para resolución manual.
        
        Args:
            entity_type: Tipo de entidad (candidate, job)
            entity_id: ID de la entidad
            local_data: Datos locales
            remote_data: Datos remotos
        """
        conflict_data = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "local_data": local_data,
            "remote_data": remote_data,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        
        # Guardar en cache/BD para revisión manual
        cache_key = f"conflict:{entity_type}:{entity_id}"
        await cache.set(cache_key, conflict_data, ttl=86400 * 30)  # 30 días
        
        logger.info(f"Queued conflict for manual resolution: {entity_type} {entity_id}")
