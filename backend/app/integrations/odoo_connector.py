"""Odoo connector with XML-RPC/JSON-RPC support and bidirectional sync."""
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.base import (
    BaseConnector,
    CircuitBreakerConfig,
    RateLimitConfig,
    SyncResult,
    WebhookHandler,
    with_retry,
)
from app.models import Candidate, JobOpening, CandidateStatus, JobStatus
from app.schemas import OdooConfig

logger = logging.getLogger(__name__)


@dataclass
class OdooRateLimits:
    """Rate limits de Odoo API."""
    # Odoo no tiene límites estrictos, pero es buena práctica ser conservador
    REQUESTS_PER_SECOND = 10
    BURST_SIZE = 20
    
    # Batch limits - Odoo puede manejar grandes batches pero hay que ser cuidadoso
    MAX_BATCH_SIZE = 1000


@dataclass
class OdooConnectionInfo:
    """Información de conexión a Odoo."""
    url: str
    database: str
    user_id: int
    username: str
    api_key: str
    context: Dict[str, Any]


class OdooConnector(BaseConnector[OdooConfig]):
    """Conector para Odoo ERP via JSON-RPC.
    
    Features:
    - Conexión via JSON-RPC (más moderno que XML-RPC)
    - Sync bidireccional de hr.job y hr.applicant
    - Mapeo flexible de campos
    - Soporte para campos personalizados (x_)
    
    Modelos Odoo utilizados:
    - hr.job: Puestos de trabajo
    - hr.applicant: Candidatos/postulantes
    - hr.recruitment.stage: Etapas del proceso
    """
    
    # Endpoints JSON-RPC
    JSONRPC_ENDPOINT = "/jsonrpc"
    
    # Scopes mínimos (en Odoo se configuran permisos por usuario)
    REQUIRED_PERMISSIONS = [
        "hr_recruitment.group_hr_recruitment_user",  # Usuario de reclutamiento
    ]
    
    # Mapeo de campos Odoo hr.job -> ATS Platform
    DEFAULT_JOB_MAPPING = {
        "id": "external_id",
        "name": "title",
        "description": "description",
        "department_id": "department",  # [id, name]
        "address_id": "location",  # [id, name] - ubicación
        "no_of_recruitment": "open_positions",
        "state": "status",
        "create_date": "created_at",
        "write_date": "updated_at",
        "x_zoho_job_id": "zoho_job_id",  # Campo personalizado para sincronización
    }
    
    # Mapeo de campos Odoo hr.applicant -> ATS Platform
    DEFAULT_CANDIDATE_MAPPING = {
        "id": "external_id",
        "name": "full_name",
        "partner_name": "full_name",
        "email_from": "email",
        "partner_mobile": "phone",
        "partner_phone": "phone",
        "job_id": "job_id",  # [id, name]
        "stage_id": "status",  # [id, name]
        "type_id": "source",  # [id, name] - fuente
        "salary_expected": "expected_salary",
        "salary_proposed": "proposed_salary",
        "availability": "availability",
        "description": "cover_letter",
        "create_date": "created_at",
        "write_date": "updated_at",
        "x_linkedin_url": "linkedin_url",  # Campo personalizado
        "x_zoho_candidate_id": "zoho_candidate_id",  # Campo personalizado
    }
    
    # Mapeo de estados de Odoo a nuestros estados
    JOB_STATUS_MAP = {
        "recruit": JobStatus.ACTIVE.value,
        "open": JobStatus.ACTIVE.value,
        "done": JobStatus.CLOSED.value,
    }
    
    CANDIDATE_STAGE_MAP = {
        "New": CandidateStatus.NEW.value,
        "Initial Qualification": CandidateStatus.SCREENING.value,
        "First Interview": CandidateStatus.INTERVIEW.value,
        "Second Interview": CandidateStatus.INTERVIEW.value,
        "Contract Proposal": CandidateStatus.OFFER.value,
        "Contract Signed": CandidateStatus.HIRED.value,
        "Refused": CandidateStatus.REJECTED.value,
        "Cancelled": CandidateStatus.REJECTED.value,
    }
    
    def __init__(
        self,
        db: AsyncSession,
        config: OdooConfig,
        job_mapping: Optional[Dict[str, str]] = None,
        candidate_mapping: Optional[Dict[str, str]] = None,
    ):
        rate_config = RateLimitConfig(
            requests_per_second=OdooRateLimits.REQUESTS_PER_SECOND,
            burst_size=OdooRateLimits.BURST_SIZE,
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0
        )
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            half_open_max_calls=3,
            success_threshold=2
        )
        
        super().__init__(db, config, rate_config, circuit_config)
        self.connection_info: Optional[OdooConnectionInfo] = None
        self.job_mapping = job_mapping or self.DEFAULT_JOB_MAPPING.copy()
        self.candidate_mapping = candidate_mapping or self.DEFAULT_CANDIDATE_MAPPING.copy()
        self._uid: Optional[int] = None
    
    async def __aenter__(self):
        await super().__aenter__()
        await self.authenticate()
        return self
    
    def _get_jsonrpc_url(self) -> str:
        """Obtener URL del endpoint JSON-RPC."""
        base_url = self.config.url.rstrip("/")
        return f"{base_url}{self.JSONRPC_ENDPOINT}"
    
    async def _jsonrpc_call(
        self,
        service: str,
        method: str,
        args: List[Any],
        retry_count: int = 0
    ) -> Any:
        """Realizar llamada JSON-RPC a Odoo.
        
        Args:
            service: Servicio (common, object, db)
            method: Método a llamar
            args: Argumentos
            retry_count: Contador de reintentos
            
        Returns:
            Resultado de la llamada
        """
        await self.rate_limiter.acquire()
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": args
            },
            "id": datetime.utcnow().timestamp()
        }
        
        async def do_call():
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")
            
            response = await self.http_client.post(
                self._get_jsonrpc_url(),
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            if "error" in result:
                error = result["error"]
                raise OdooAPIError(
                    f"Odoo API Error: {error.get('message', 'Unknown error')}",
                    code=error.get("code"),
                    data=error.get("data")
                )
            
            return result.get("result")
        
        try:
            return await self.circuit_breaker.call(do_call)
        except Exception as e:
            # Retry en errores de conexión
            if retry_count < self.rate_limiter.config.max_retries:
                import asyncio
                delay = min(
                    self.rate_limiter.config.base_delay * (2 ** retry_count),
                    self.rate_limiter.config.max_delay
                )
                await asyncio.sleep(delay)
                return await self._jsonrpc_call(service, method, args, retry_count + 1)
            raise
    
    @with_retry(max_retries=3, base_delay=1.0)
    async def authenticate(self) -> bool:
        """Autenticar con Odoo.
        
        Returns:
            True si la autenticación fue exitosa.
        """
        try:
            # Login para obtener user ID
            uid = await self._jsonrpc_call(
                "common",
                "login",
                [self.config.database, self.config.username, self.config.api_key]
            )
            
            if not uid:
                logger.error("Odoo authentication failed: Invalid credentials")
                return False
            
            self._uid = uid
            
            # Obtener contexto del usuario
            context = await self._jsonrpc_call(
                "object",
                "execute_kw",
                [
                    self.config.database,
                    uid,
                    self.config.api_key,
                    "res.users",
                    "context_get",
                    []
                ]
            )
            
            self.connection_info = OdooConnectionInfo(
                url=self.config.url,
                database=self.config.database,
                user_id=uid,
                username=self.config.username,
                api_key=self.config.api_key,
                context=context or {}
            )
            
            logger.info(f"Authenticated with Odoo as {self.config.username} (UID: {uid})")
            return True
            
        except Exception as e:
            logger.error(f"Odoo authentication failed: {e}")
            return False
    
    async def test_connection(self) -> Tuple[bool, str]:
        """Probar conexión con Odoo.
        
        Returns:
            (success, message)
        """
        try:
            # Intentar obtener versión (no requiere auth)
            version = await self._jsonrpc_call("common", "version", [])
            
            if not self.connection_info:
                return False, "Not authenticated"
            
            # Verificar permisos listando jobs
            jobs_count = await self._execute_kw(
                self.config.job_model,
                "search_count",
                [[]]
            )
            
            return True, f"Connected to Odoo {version.get('server_version', 'unknown')} - {jobs_count} jobs available"
            
        except OdooAPIError as e:
            return False, f"Odoo API Error: {e.message}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    async def _execute_kw(
        self,
        model: str,
        method: str,
        args: List[Any],
        kwargs: Optional[Dict] = None
    ) -> Any:
        """Ejecutar método en modelo Odoo.
        
        Args:
            model: Nombre del modelo (ej: hr.job)
            method: Método (search, read, create, write, unlink)
            args: Argumentos posicionales
            kwargs: Argumentos nombrados
            
        Returns:
            Resultado de la operación
        """
        if not self.connection_info:
            raise RuntimeError("Not authenticated")
        
        call_args = [
            self.connection_info.database,
            self.connection_info.user_id,
            self.connection_info.api_key,
            model,
            method,
            args
        ]
        
        if kwargs:
            call_args.append(kwargs)
        
        return await self._jsonrpc_call("object", "execute_kw", call_args)
    
    # ==================== SYNC OPERATIONS ====================
    
    async def sync_jobs(
        self,
        modified_since: Optional[datetime] = None,
        full_sync: bool = False,
        domain: Optional[List] = None
    ) -> SyncResult:
        """Sincronizar jobs (hr.job) desde Odoo.
        
        Args:
            modified_since: Solo jobs modificados después de esta fecha
            full_sync: Si True, sincronizar todos
            domain: Filtro de dominio adicional de Odoo
            
        Returns:
            Resultado de la sincronización
        """
        start_time = datetime.utcnow()
        result = SyncResult(success=True)
        
        try:
            # Construir dominio de búsqueda
            search_domain = domain or []
            if not full_sync and modified_since:
                search_domain.append(("write_date", ">=", modified_since.isoformat()))
            
            # Buscar IDs
            job_ids = await self._execute_kw(
                self.config.job_model,
                "search",
                [search_domain],
                {"order": "write_date desc"}
            )
            
            if not job_ids:
                logger.info("No jobs to sync from Odoo")
                return result
            
            # Leer datos en batches
            batch_size = OdooRateLimits.MAX_BATCH_SIZE
            for i in range(0, len(job_ids), batch_size):
                batch_ids = job_ids[i:i + batch_size]
                
                jobs_data = await self._execute_kw(
                    self.config.job_model,
                    "read",
                    [batch_ids],
                    {"fields": list(self.job_mapping.keys())}
                )
                
                batch_result = await self._process_jobs_batch(jobs_data)
                result = result.merge(batch_result)
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Job sync from Odoo failed: {e}")
            result.success = False
            result.errors.append(str(e))
        
        result.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return result
    
    async def _process_jobs_batch(self, jobs_data: List[Dict]) -> SyncResult:
        """Procesar un batch de jobs de Odoo."""
        result = SyncResult(success=True)
        
        for job_data in jobs_data:
            try:
                odoo_job_id = str(job_data.get("id"))
                if not odoo_job_id:
                    result.warnings.append(f"Job without ID: {job_data}")
                    result.items_failed += 1
                    continue
                
                # Buscar job existente (por external_id o zoho_job_id si existe campo personalizado)
                existing = await self.db.execute(
                    select(JobOpening).where(
                        (JobOpening.zoho_job_id == odoo_job_id) |
                        (JobOpening.external_id == odoo_job_id)
                    )
                )
                job = existing.scalar_one_or_none()
                
                # Mapear campos
                mapped_data = self._map_job_fields(job_data)
                mapped_data["external_id"] = odoo_job_id
                
                if job:
                    # Actualizar
                    for key, value in mapped_data.items():
                        if hasattr(job, key) and value is not None:
                            setattr(job, key, value)
                    job.updated_at = datetime.utcnow()
                    result.items_updated += 1
                else:
                    # Crear nuevo
                    mapped_data["source"] = "odoo"
                    job = JobOpening(**mapped_data)
                    self.db.add(job)
                    result.items_created += 1
                
                result.items_processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process Odoo job {job_data.get('id')}: {e}")
                result.items_failed += 1
                result.errors.append(str(e))
        
        await self.db.commit()
        return result
    
    def _map_job_fields(self, odoo_data: Dict) -> Dict[str, Any]:
        """Mapear campos de Odoo hr.job a nuestro modelo."""
        result = {}
        
        for odoo_field, our_field in self.job_mapping.items():
            value = odoo_data.get(odoo_field)
            if value is not None:
                # Manejar campos relación [id, name]
                if isinstance(value, list) and len(value) >= 2:
                    value = value[1]  # Tomar el nombre
                result[our_field] = value
        
        # Mapear estado
        if "status" in result:
            result["status"] = self.JOB_STATUS_MAP.get(
                result["status"], 
                JobStatus.DRAFT.value
            )
        
        # Convertir description de HTML a texto plano si es necesario
        if "description" in result and result["description"]:
            result["description"] = self._strip_html(result["description"])
        
        return result
    
    async def sync_candidates(
        self,
        modified_since: Optional[datetime] = None,
        full_sync: bool = False,
        job_id: Optional[int] = None,
        domain: Optional[List] = None
    ) -> SyncResult:
        """Sincronizar candidatos (hr.applicant) desde Odoo.
        
        Args:
            modified_since: Solo candidatos modificados después de esta fecha
            full_sync: Si True, sincronizar todos
            job_id: Filtrar por ID de job en Odoo
            domain: Filtro de dominio adicional
            
        Returns:
            Resultado de la sincronización
        """
        start_time = datetime.utcnow()
        result = SyncResult(success=True)
        
        try:
            # Construir dominio
            search_domain = domain or []
            if not full_sync and modified_since:
                search_domain.append(("write_date", ">=", modified_since.isoformat()))
            if job_id:
                search_domain.append(("job_id", "=", job_id))
            
            # Buscar IDs
            candidate_ids = await self._execute_kw(
                self.config.applicant_model,
                "search",
                [search_domain],
                {"order": "write_date desc"}
            )
            
            if not candidate_ids:
                logger.info("No candidates to sync from Odoo")
                return result
            
            # Leer en batches
            batch_size = OdooRateLimits.MAX_BATCH_SIZE
            for i in range(0, len(candidate_ids), batch_size):
                batch_ids = candidate_ids[i:i + batch_size]
                
                candidates_data = await self._execute_kw(
                    self.config.applicant_model,
                    "read",
                    [batch_ids],
                    {"fields": list(self.candidate_mapping.keys())}
                )
                
                batch_result = await self._process_candidates_batch(candidates_data)
                result = result.merge(batch_result)
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Candidate sync from Odoo failed: {e}")
            result.success = False
            result.errors.append(str(e))
        
        result.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return result
    
    async def _process_candidates_batch(self, candidates_data: List[Dict]) -> SyncResult:
        """Procesar un batch de candidatos de Odoo."""
        result = SyncResult(success=True)
        
        for candidate_data in candidates_data:
            try:
                odoo_candidate_id = str(candidate_data.get("id"))
                if not odoo_candidate_id:
                    result.warnings.append(f"Candidate without ID: {candidate_data}")
                    result.items_failed += 1
                    continue
                
                # Buscar candidato existente
                zoho_id = candidate_data.get("x_zoho_candidate_id")
                
                if zoho_id:
                    existing = await self.db.execute(
                        select(Candidate).where(Candidate.zoho_candidate_id == zoho_id)
                    )
                else:
                    existing = await self.db.execute(
                        select(Candidate).where(Candidate.external_id == odoo_candidate_id)
                    )
                
                candidate = existing.scalar_one_or_none()
                
                # Mapear campos
                mapped_data = self._map_candidate_fields(candidate_data)
                mapped_data["external_id"] = odoo_candidate_id
                
                # Buscar job relacionado
                job_odoo_id = candidate_data.get("job_id")
                if job_odoo_id and isinstance(job_odoo_id, list):
                    job_odoo_id = job_odoo_id[0]  # ID es el primer elemento
                    
                    job_result = await self.db.execute(
                        select(JobOpening).where(
                            (JobOpening.external_id == str(job_odoo_id)) |
                            (JobOpening.zoho_job_id == str(job_odoo_id))
                        )
                    )
                    job = job_result.scalar_one_or_none()
                    if job:
                        mapped_data["job_opening_id"] = job.id
                
                if candidate:
                    # Actualizar
                    for key, value in mapped_data.items():
                        if hasattr(candidate, key) and value is not None:
                            setattr(candidate, key, value)
                    candidate.updated_at = datetime.utcnow()
                    result.items_updated += 1
                else:
                    # Crear nuevo
                    mapped_data["source"] = "odoo"
                    candidate = Candidate(**mapped_data)
                    self.db.add(candidate)
                    result.items_created += 1
                
                result.items_processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process Odoo candidate {candidate_data.get('id')}: {e}")
                result.items_failed += 1
                result.errors.append(str(e))
        
        await self.db.commit()
        return result
    
    def _map_candidate_fields(self, odoo_data: Dict) -> Dict[str, Any]:
        """Mapear campos de Odoo hr.applicant a nuestro modelo."""
        result = {}
        
        for odoo_field, our_field in self.candidate_mapping.items():
            value = odoo_data.get(odoo_field)
            if value is not None:
                # Manejar campos relación
                if isinstance(value, list) and len(value) >= 2:
                    if our_field == "status":
                        # Para stage_id, mapear el nombre a nuestro status
                        stage_name = value[1]
                        value = self.CANDIDATE_STAGE_MAP.get(
                            stage_name,
                            CandidateStatus.NEW.value
                        )
                    else:
                        value = value[1]  # Tomar el nombre
                result[our_field] = value
        
        # Normalizar email
        if "email" in result:
            result["email_normalized"] = result["email"].lower().strip() if result["email"] else None
        
        # Normalizar teléfono
        if "phone" in result and result["phone"]:
            phone = result["phone"]
            result["phone_normalized"] = ''.join(c for c in phone if c.isdigit())
        
        # Guardar raw_data
        result["raw_data"] = odoo_data
        
        return result
    
    # ==================== BIDIRECTIONAL SYNC (ATS -> Odoo) ====================
    
    async def push_job_to_odoo(self, job: JobOpening) -> Tuple[bool, Optional[int]]:
        """Enviar job a Odoo (crear o actualizar).
        
        Args:
            job: JobOpening de nuestro sistema
            
        Returns:
            (success, odoo_id)
        """
        try:
            # Preparar datos
            values = {
                "name": job.title,
                "description": job.description or "",
                "department_id": False,  # Buscar o crear
                "no_of_recruitment": 1,
                "state": "recruit" if job.is_active else "done",
            }
            
            if job.department:
                # Buscar departamento
                dept_ids = await self._execute_kw(
                    "hr.department",
                    "search",
                    [[("name", "=", job.department)]]
                )
                if dept_ids:
                    values["department_id"] = dept_ids[0]
            
            if job.external_id:
                # Actualizar existente
                await self._execute_kw(
                    self.config.job_model,
                    "write",
                    [[int(job.external_id)], values]
                )
                return True, int(job.external_id)
            else:
                # Crear nuevo
                odoo_id = await self._execute_kw(
                    self.config.job_model,
                    "create",
                    [values]
                )
                # Actualizar referencia
                job.external_id = str(odoo_id)
                await self.db.commit()
                return True, odoo_id
                
        except Exception as e:
            logger.error(f"Failed to push job to Odoo: {e}")
            return False, None
    
    async def push_candidate_to_odoo(self, candidate: Candidate) -> Tuple[bool, Optional[int]]:
        """Enviar candidato a Odoo (crear o actualizar).
        
        Args:
            candidate: Candidate de nuestro sistema
            
        Returns:
            (success, odoo_id)
        """
        try:
            # Preparar datos
            values = {
                "name": candidate.full_name or "Unknown",
                "email_from": candidate.email or "",
                "partner_mobile": candidate.phone or "",
            }
            
            # Buscar job en Odoo
            if candidate.job_opening_id:
                job = await self.db.get(JobOpening, candidate.job_opening_id)
                if job and job.external_id:
                    values["job_id"] = int(job.external_id)
            
            # Mapear estado
            stage_ids = await self._execute_kw(
                "hr.recruitment.stage",
                "search",
                [[]]
            )
            if stage_ids:
                # Por simplicidad, usar la primera etapa
                values["stage_id"] = stage_ids[0]
            
            if candidate.external_id and candidate.source == "odoo":
                # Actualizar existente
                await self._execute_kw(
                    self.config.applicant_model,
                    "write",
                    [[int(candidate.external_id)], values]
                )
                return True, int(candidate.external_id)
            else:
                # Crear nuevo
                odoo_id = await self._execute_kw(
                    self.config.applicant_model,
                    "create",
                    [values]
                )
                candidate.external_id = str(odoo_id)
                candidate.source = "odoo"
                await self.db.commit()
                return True, odoo_id
                
        except Exception as e:
            logger.error(f"Failed to push candidate to Odoo: {e}")
            return False, None
    
    # ==================== UTILITY METHODS ====================
    
    def _strip_html(self, html: str) -> str:
        """Remover tags HTML de un string."""
        import re
        # Patrón simple para remover tags HTML
        clean = re.compile('<.*?>')
        return re.sub(clean, '', html)
    
    def get_webhook_handler(self) -> 'OdooWebhookHandler':
        """Obtener handler de webhooks."""
        return OdooWebhookHandler(self)


class OdooAPIError(Exception):
    """Error de API de Odoo."""
    
    def __init__(self, message: str, code: Optional[int] = None, data: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data


class OdooWebhookHandler(WebhookHandler):
    """Handler para webhooks de Odoo.
    
    Odoo soporta webhooks via módulos adicionales o usando
    el sistema de automatizaciones (automated actions).
    """
    
    async def handle(self, payload: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """Procesar webhook de Odoo.
        
        El formato esperado es:
        {
            "model": "hr.applicant" | "hr.job",
            "id": int,
            "action": "create" | "write" | "unlink",
            "data": {...}
        }
        """
        try:
            data = json.loads(payload)
            
            model = data.get("model")
            action = data.get("action")
            record_data = data.get("data", {})
            
            if not model or not action:
                return {"success": False, "error": "Missing model or action"}
            
            connector = self.connector  # type: OdooConnector
            
            if model == connector.config.job_model:
                if action in ["create", "write"]:
                    result = await connector._process_jobs_batch([record_data])
                elif action == "unlink":
                    # Marcar como inactivo
                    odoo_id = str(record_data.get("id"))
                    if odoo_id:
                        result = await connector.db.execute(
                            select(JobOpening).where(JobOpening.external_id == odoo_id)
                        )
                        job = result.scalar_one_or_none()
                        if job:
                            job.is_active = False
                            await connector.db.commit()
                    result = SyncResult(success=True, items_processed=1)
                else:
                    return {"success": False, "error": f"Unknown action: {action}"}
                    
            elif model == connector.config.applicant_model:
                if action in ["create", "write"]:
                    result = await connector._process_candidates_batch([record_data])
                elif action == "unlink":
                    odoo_id = str(record_data.get("id"))
                    if odoo_id:
                        result = await connector.db.execute(
                            select(Candidate).where(Candidate.external_id == odoo_id)
                        )
                        candidate = result.scalar_one_or_none()
                        if candidate:
                            candidate.status = CandidateStatus.REJECTED.value
                            await connector.db.commit()
                    result = SyncResult(success=True, items_processed=1)
                else:
                    return {"success": False, "error": f"Unknown action: {action}"}
            else:
                return {"success": False, "error": f"Unknown model: {model}"}
            
            return {
                "success": result.success,
                "processed": result.items_processed,
                "created": result.items_created,
                "updated": result.items_updated,
                "errors": result.errors
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {e}")
            return {"success": False, "error": "Invalid JSON"}
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return {"success": False, "error": str(e)}
    
    def verify_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verificar firma del webhook.
        
        Odoo puede configurarse para enviar un token de verificación
        en los headers o como query parameter.
        """
        if not signature or not secret:
            return False
        # Comparación simple de token
        return signature == secret
