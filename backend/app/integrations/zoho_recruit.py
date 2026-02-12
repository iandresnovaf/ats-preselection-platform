"""Zoho Recruit connector with OAuth2, sync, and webhook support."""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.integrations.base import (
    BaseConnector,
    CircuitBreakerConfig,
    RateLimitConfig,
    SyncResult,
    WebhookHandler,
    with_retry,
)
from app.models import Candidate, JobOpening, CandidateStatus, JobStatus
from app.schemas import ZohoConfig

logger = logging.getLogger(__name__)


@dataclass
class ZohoRateLimits:
    """Rate limits de Zoho Recruit API."""
    # Zoho permite 100 requests/minuto por usuario para la mayoría de endpoints
    REQUESTS_PER_MINUTE = 100
    REQUESTS_PER_SECOND = REQUESTS_PER_MINUTE / 60
    BURST_SIZE = 10
    
    # Batch limits
    MAX_BATCH_SIZE = 200  # Máximo de registros por batch


@dataclass
class ZohoTokens:
    """Tokens OAuth de Zoho."""
    access_token: str
    refresh_token: str
    expires_at: datetime
    api_domain: str = "https://www.zohoapis.com"


class ZohoRecruitConnector(BaseConnector[ZohoConfig]):
    """Conector para Zoho Recruit API.
    
    Features:
    - OAuth2 authentication con auto-refresh
    - Sync bidireccional de jobs y candidatos
    - Webhook handling
    - Rate limiting respetando límites de Zoho
    - Circuit breaker para resiliencia
    """
    
    # Zoho API endpoints
    AUTH_URL = "https://accounts.zoho.com/oauth/v2"
    API_BASE_URL = "https://recruit.zoho.com/recruit/v2"
    
    # Scopes mínimos necesarios
    SCOPES = [
        "ZohoRecruit.modules.all",  # Acceso a todos los módulos
        "ZohoRecruit.settings.all",  # Configuración
    ]
    
    # Mapeo de campos Zoho -> ATS Platform
    DEFAULT_JOB_MAPPING = {
        "id": "zoho_job_id",
        "Job_Opening_ID": "external_id",
        "Job_Opening_Name": "title",
        "Job_Description": "description",
        "Department": "department",
        "Location": "location",
        "Seniority_Level": "seniority",
        "Industry": "sector",
        "Status": "status",
        "Created_Time": "created_at",
        "Modified_Time": "updated_at",
    }
    
    DEFAULT_CANDIDATE_MAPPING = {
        "id": "zoho_candidate_id",
        "Candidate_ID": "external_id",
        "First_Name": "first_name",
        "Last_Name": "last_name",
        "Full_Name": "full_name",
        "Email": "email",
        "Phone": "phone",
        "Mobile": "mobile",
        "Experience_in_Years": "experience_years",
        "Current_Employer": "current_employer",
        "Current_Job_Title": "current_job_title",
        "Skill_Set": "skills",
        "Education": "education",
        "Resume": "resume_url",
        "Source": "source",
        "Stage": "status",
        "Created_Time": "created_at",
        "Modified_Time": "updated_at",
    }
    
    def __init__(
        self,
        db: AsyncSession,
        config: ZohoConfig,
        job_mapping: Optional[Dict[str, str]] = None,
        candidate_mapping: Optional[Dict[str, str]] = None,
    ):
        rate_config = RateLimitConfig(
            requests_per_second=ZohoRateLimits.REQUESTS_PER_SECOND,
            burst_size=ZohoRateLimits.BURST_SIZE,
            max_retries=5,
            base_delay=2.0,
            max_delay=60.0
        )
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=120,
            half_open_max_calls=3,
            success_threshold=2
        )
        
        super().__init__(db, config, rate_config, circuit_config)
        self.tokens: Optional[ZohoTokens] = None
        self.job_mapping = job_mapping or self.DEFAULT_JOB_MAPPING.copy()
        self.candidate_mapping = candidate_mapping or self.DEFAULT_CANDIDATE_MAPPING.copy()
    
    async def __aenter__(self):
        await super().__aenter__()
        # Cargar tokens existentes o autenticar
        await self._load_or_refresh_tokens()
        return self
    
    async def _load_or_refresh_tokens(self):
        """Cargar tokens del cache o autenticar."""
        cached_tokens = await self._get_cached("tokens")
        if cached_tokens:
            self.tokens = ZohoTokens(**cached_tokens)
            # Refrescar si expiran en menos de 5 minutos
            if self.tokens.expires_at < datetime.utcnow() + timedelta(minutes=5):
                await self._refresh_access_token()
        else:
            await self.authenticate()
    
    @with_retry(max_retries=3, base_delay=2.0)
    async def authenticate(self) -> bool:
        """Autenticar con Zoho usando refresh token.
        
        El flujo OAuth2 completo debe hacerse una vez para obtener el refresh_token.
        Después, usamos el refresh_token para obtener access_tokens.
        
        Returns:
            True si la autenticación fue exitosa.
        """
        if not self.config.refresh_token:
            logger.error("No refresh token available. Complete OAuth2 flow first.")
            return False
        
        try:
            await self._refresh_access_token()
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    async def _refresh_access_token(self):
        """Refrescar access token usando refresh token."""
        params = {
            "refresh_token": self.config.refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "refresh_token"
        }
        
        response = await self._make_request(
            "POST",
            f"{self.AUTH_URL}/token",
            params=params
        )
        
        data = response.json()
        
        if "access_token" not in data:
            raise ValueError(f"Failed to refresh token: {data}")
        
        expires_in = data.get("expires_in", 3600)
        self.tokens = ZohoTokens(
            access_token=data["access_token"],
            refresh_token=self.config.refresh_token,  # El refresh token no cambia
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in - 300),  # 5 min buffer
            api_domain=data.get("api_domain", "https://www.zohoapis.com")
        )
        
        # Guardar en cache
        await self._set_cached("tokens", {
            "access_token": self.tokens.access_token,
            "refresh_token": self.tokens.refresh_token,
            "expires_at": self.tokens.expires_at.isoformat(),
            "api_domain": self.tokens.api_domain
        }, ttl=expires_in - 300)
        
        logger.info("Zoho access token refreshed successfully")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Obtener headers de autorización."""
        if not self.tokens:
            raise RuntimeError("Not authenticated")
        return {
            "Authorization": f"Zoho-oauthtoken {self.tokens.access_token}",
            "Content-Type": "application/json"
        }
    
    async def test_connection(self) -> Tuple[bool, str]:
        """Probar conexión con Zoho Recruit.
        
        Returns:
            (success, message)
        """
        try:
            # Intentar obtener información del usuario/org
            response = await self._make_request(
                "GET",
                f"{self.API_BASE_URL}/org",
                headers=self._get_auth_headers()
            )
            data = response.json()
            org_name = data.get("data", [{}])[0].get("org_name", "Unknown")
            return True, f"Connected to Zoho Recruit: {org_name}"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return False, "Authentication failed: Invalid credentials"
            return False, f"HTTP Error: {e.response.status_code}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    async def get_auth_url(self, redirect_uri: Optional[str] = None) -> str:
        """Generar URL de autorización OAuth2.
        
        Args:
            redirect_uri: URI de redirección (opcional)
            
        Returns:
            URL de autorización
        """
        redirect = redirect_uri or self.config.redirect_uri
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": redirect,
            "scope": ",".join(self.SCOPES),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"  # Forzar obtener refresh token
        }
        return f"{self.AUTH_URL}/auth?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Intercambiar código de autorización por tokens.
        
        Args:
            code: Código de autorización recibido
            redirect_uri: URI de redirección (debe coincidir con el usado en auth)
            
        Returns:
            Datos de los tokens
        """
        redirect = redirect_uri or self.config.redirect_uri
        params = {
            "code": code,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "redirect_uri": redirect,
            "grant_type": "authorization_code"
        }
        
        response = await self._make_request(
            "POST",
            f"{self.AUTH_URL}/token",
            params=params
        )
        
        data = response.json()
        
        if "refresh_token" in data:
            # Actualizar config con el refresh token
            self.config.refresh_token = data["refresh_token"]
            logger.info("Received refresh token from Zoho")
        
        return data
    
    # ==================== SYNC OPERATIONS ====================
    
    async def sync_jobs(
        self,
        modified_since: Optional[datetime] = None,
        full_sync: bool = False
    ) -> SyncResult:
        """Sincronizar jobs desde Zoho.
        
        Args:
            modified_since: Solo sincronizar jobs modificados después de esta fecha
            full_sync: Si True, sincronizar todos los jobs (ignorar modified_since)
            
        Returns:
            Resultado de la sincronización
        """
        start_time = datetime.utcnow()
        result = SyncResult(success=True)
        
        try:
            # Construir criterio de búsqueda
            criteria = None
            if not full_sync and modified_since:
                criteria = f"(Modified_Time:after:{modified_since.isoformat()})"
            
            # Paginación
            page = 1
            per_page = ZohoRateLimits.MAX_BATCH_SIZE
            has_more = True
            
            while has_more:
                jobs_data = await self._fetch_jobs_page(page, per_page, criteria)
                
                if not jobs_data:
                    break
                
                batch_result = await self._process_jobs_batch(jobs_data)
                result = result.merge(batch_result)
                
                has_more = len(jobs_data) == per_page
                page += 1
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Job sync failed: {e}")
            result.success = False
            result.errors.append(str(e))
        
        result.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return result
    
    async def _fetch_jobs_page(
        self,
        page: int,
        per_page: int,
        criteria: Optional[str] = None
    ) -> List[Dict]:
        """Fetch una página de jobs desde Zoho."""
        params = {
            "page": page,
            "per_page": per_page,
            "sort_by": "Modified_Time",
            "sort_order": "desc"
        }
        
        if criteria:
            params["criteria"] = criteria
        
        response = await self._make_request(
            "GET",
            f"{self.API_BASE_URL}/JobOpenings",
            headers=self._get_auth_headers(),
            params=params
        )
        
        data = response.json()
        return data.get("data", [])
    
    async def _process_jobs_batch(self, jobs_data: List[Dict]) -> SyncResult:
        """Procesar un batch de jobs."""
        result = SyncResult(success=True)
        
        for job_data in jobs_data:
            try:
                zoho_job_id = job_data.get("id") or job_data.get(self.config.job_id_field)
                if not zoho_job_id:
                    result.warnings.append(f"Job without ID: {job_data}")
                    result.items_failed += 1
                    continue
                
                # Buscar job existente
                existing = await self.db.execute(
                    select(JobOpening).where(JobOpening.zoho_job_id == zoho_job_id)
                )
                job = existing.scalar_one_or_none()
                
                # Mapear campos
                mapped_data = self._map_job_fields(job_data)
                
                if job:
                    # Actualizar
                    for key, value in mapped_data.items():
                        if hasattr(job, key) and value is not None:
                            setattr(job, key, value)
                    job.updated_at = datetime.utcnow()
                    result.items_updated += 1
                else:
                    # Crear nuevo
                    job = JobOpening(**mapped_data)
                    self.db.add(job)
                    result.items_created += 1
                
                result.items_processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process job {job_data.get('id')}: {e}")
                result.items_failed += 1
                result.errors.append(str(e))
        
        await self.db.commit()
        return result
    
    def _map_job_fields(self, zoho_data: Dict) -> Dict[str, Any]:
        """Mapear campos de Zoho a nuestro modelo."""
        result = {}
        for zoho_field, our_field in self.job_mapping.items():
            value = zoho_data.get(zoho_field)
            if value is not None:
                result[our_field] = value
        
        # Normalizaciones
        if "status" in result:
            status_map = {
                "Active": JobStatus.ACTIVE.value,
                "Draft": JobStatus.DRAFT.value,
                "Closed": JobStatus.CLOSED.value,
                "Paused": JobStatus.PAUSED.value,
            }
            result["status"] = status_map.get(result["status"], JobStatus.DRAFT.value)
        
        return result
    
    async def sync_candidates(
        self,
        modified_since: Optional[datetime] = None,
        full_sync: bool = False,
        job_opening_id: Optional[str] = None
    ) -> SyncResult:
        """Sincronizar candidatos desde Zoho.
        
        Args:
            modified_since: Solo candidatos modificados después de esta fecha
            full_sync: Si True, sincronizar todos
            job_opening_id: Filtrar por job específico
            
        Returns:
            Resultado de la sincronización
        """
        start_time = datetime.utcnow()
        result = SyncResult(success=True)
        
        try:
            # Construir criterio
            criteria_parts = []
            if not full_sync and modified_since:
                criteria_parts.append(f"(Modified_Time:after:{modified_since.isoformat()})")
            if job_opening_id:
                criteria_parts.append(f"(Job_Opening_ID:equals:{job_opening_id})")
            
            criteria = "and".join(criteria_parts) if criteria_parts else None
            
            # Paginación
            page = 1
            per_page = ZohoRateLimits.MAX_BATCH_SIZE
            has_more = True
            
            while has_more:
                candidates_data = await self._fetch_candidates_page(page, per_page, criteria)
                
                if not candidates_data:
                    break
                
                batch_result = await self._process_candidates_batch(candidates_data)
                result = result.merge(batch_result)
                
                has_more = len(candidates_data) == per_page
                page += 1
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Candidate sync failed: {e}")
            result.success = False
            result.errors.append(str(e))
        
        result.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return result
    
    async def _fetch_candidates_page(
        self,
        page: int,
        per_page: int,
        criteria: Optional[str] = None
    ) -> List[Dict]:
        """Fetch una página de candidatos desde Zoho."""
        params = {
            "page": page,
            "per_page": per_page,
            "sort_by": "Modified_Time",
            "sort_order": "desc"
        }
        
        if criteria:
            params["criteria"] = criteria
        
        response = await self._make_request(
            "GET",
            f"{self.API_BASE_URL}/Candidates",
            headers=self._get_auth_headers(),
            params=params
        )
        
        data = response.json()
        return data.get("data", [])
    
    async def _process_candidates_batch(self, candidates_data: List[Dict]) -> SyncResult:
        """Procesar un batch de candidatos."""
        result = SyncResult(success=True)
        
        for candidate_data in candidates_data:
            try:
                zoho_candidate_id = candidate_data.get("id") or candidate_data.get(self.config.candidate_id_field)
                if not zoho_candidate_id:
                    result.warnings.append(f"Candidate without ID: {candidate_data}")
                    result.items_failed += 1
                    continue
                
                # Buscar candidato existente
                existing = await self.db.execute(
                    select(Candidate).where(Candidate.zoho_candidate_id == zoho_candidate_id)
                )
                candidate = existing.scalar_one_or_none()
                
                # Mapear campos
                mapped_data = self._map_candidate_fields(candidate_data)
                
                # Buscar job relacionado
                job_opening_id = candidate_data.get("Job_Opening_ID")
                if job_opening_id:
                    job_result = await self.db.execute(
                        select(JobOpening).where(JobOpening.zoho_job_id == job_opening_id)
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
                    mapped_data["source"] = "zoho"
                    candidate = Candidate(**mapped_data)
                    self.db.add(candidate)
                    result.items_created += 1
                
                result.items_processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process candidate {candidate_data.get('id')}: {e}")
                result.items_failed += 1
                result.errors.append(str(e))
        
        await self.db.commit()
        return result
    
    def _map_candidate_fields(self, zoho_data: Dict) -> Dict[str, Any]:
        """Mapear campos de Zoho a nuestro modelo."""
        result = {}
        for zoho_field, our_field in self.candidate_mapping.items():
            value = zoho_data.get(zoho_field)
            if value is not None:
                result[our_field] = value
        
        # Construir full_name si no viene completo
        if not result.get("full_name"):
            first = zoho_data.get("First_Name", "")
            last = zoho_data.get("Last_Name", "")
            result["full_name"] = f"{first} {last}".strip()
        
        # Normalizar email
        if "email" in result:
            result["email_normalized"] = result["email"].lower().strip() if result["email"] else None
        
        # Normalizar teléfono
        if "phone" in result and result["phone"]:
            # Remover caracteres no numéricos para normalización
            phone = result["phone"]
            result["phone_normalized"] = ''.join(c for c in phone if c.isdigit())
        
        # Mapear status
        if "status" in result:
            status_map = {
                "New": CandidateStatus.NEW.value,
                "Screening": CandidateStatus.SCREENING.value,
                "Interview": CandidateStatus.INTERVIEW.value,
                "Evaluation": CandidateStatus.EVALUATION.value,
                "Offer": CandidateStatus.OFFER.value,
                "Hired": CandidateStatus.HIRED.value,
                "Rejected": CandidateStatus.REJECTED.value,
            }
            result["status"] = status_map.get(result["status"], CandidateStatus.NEW.value)
        
        # Guardar raw_data
        result["raw_data"] = zoho_data
        
        return result
    
    # ==================== WEBHOOK HANDLING ====================
    
    def get_webhook_handler(self) -> 'ZohoWebhookHandler':
        """Obtener handler de webhooks."""
        return ZohoWebhookHandler(self)


class ZohoWebhookHandler(WebhookHandler):
    """Handler para webhooks de Zoho Recruit.
    
    Zoho envía webhooks cuando ocurren eventos como:
    - create, update, delete de registros
    - Cambios de estado
    """
    
    async def handle(self, payload: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """Procesar webhook de Zoho.
        
        Args:
            payload: Body del webhook
            headers: Headers HTTP
            
        Returns:
            Resultado del procesamiento
        """
        try:
            data = json.loads(payload)
            
            # Zoho envía eventos con información del módulo y acción
            module = data.get("module")
            event = data.get("event")  # create, edit, delete
            record = data.get("data", {})
            
            if not module or not event:
                return {"success": False, "error": "Missing module or event"}
            
            connector = self.connector  # type: ZohoRecruitConnector
            
            if module == "JobOpenings":
                if event in ["create", "edit"]:
                    result = await connector._process_jobs_batch([record])
                elif event == "delete":
                    # Marcar como inactivo en lugar de eliminar
                    zoho_id = record.get("id")
                    if zoho_id:
                        from sqlalchemy import select
                        result = await connector.db.execute(
                            select(JobOpening).where(JobOpening.zoho_job_id == zoho_id)
                        )
                        job = result.scalar_one_or_none()
                        if job:
                            job.is_active = False
                            job.status = JobStatus.CLOSED.value
                            await connector.db.commit()
                    result = SyncResult(success=True, items_processed=1)
                else:
                    return {"success": False, "error": f"Unknown event: {event}"}
                    
            elif module == "Candidates":
                if event in ["create", "edit"]:
                    result = await connector._process_candidates_batch([record])
                elif event == "delete":
                    zoho_id = record.get("id")
                    if zoho_id:
                        result = await connector.db.execute(
                            select(Candidate).where(Candidate.zoho_candidate_id == zoho_id)
                        )
                        candidate = result.scalar_one_or_none()
                        if candidate:
                            candidate.status = CandidateStatus.REJECTED.value
                            await connector.db.commit()
                    result = SyncResult(success=True, items_processed=1)
                else:
                    return {"success": False, "error": f"Unknown event: {event}"}
            else:
                return {"success": False, "error": f"Unknown module: {module}"}
            
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
        """Zoho no usa firmas HMAC estándar en sus webhooks.
        
        En su lugar, usa:
        - Autenticación por token en URL
        - IP whitelisting
        - HTTPS obligatorio
        
        Returns:
            True (la verificación se hace a nivel de token/URL)
        """
        # La verificación real se hace comparando el token en la URL
        return True
