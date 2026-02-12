"""API endpoints para configuración del sistema."""
from typing import Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User, UserRole
from app.schemas import (
    ConfigurationCreate,
    ConfigurationUpdate,
    ConfigurationResponse,
    WhatsAppConfig,
    ZohoConfig,
    LLMConfig,
    EmailConfig,
    OdooConfig,
    SystemStatus,
    MessageResponse,
)
from app.services.configuration_service import ConfigurationService
from app.services.sync_service import SyncService, SyncSource
from app.integrations import (
    ZohoRecruitConnector,
    OdooConnector,
    LinkedInConnector,
)

router = APIRouter(prefix="/config", tags=["Configuration"])


# ============== SCHEMAS ADICIONALES ==============

class LinkedInConfig(BaseModel):
    """Configuración de LinkedIn OAuth."""
    client_id: str = Field(..., max_length=200)
    client_secret: str = Field(..., max_length=500)
    redirect_uri: str = Field(default="http://localhost:8000/api/v1/config/linkedin/callback", max_length=500)


class SyncRequest(BaseModel):
    """Request para sincronización manual."""
    full_sync: bool = False
    sync_jobs: bool = True
    sync_candidates: bool = True


class SyncResponse(BaseModel):
    """Respuesta de sincronización."""
    success: bool
    items_processed: int
    items_created: int
    items_updated: int
    items_failed: int
    duration_ms: float
    errors: list = []
    warnings: list = []


class ConnectorStatus(BaseModel):
    """Estado de un conector."""
    name: str
    connected: bool
    last_sync: Optional[str] = None
    circuit_breaker_state: str
    rate_limit_tokens: float


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency que requiere rol Super Admin."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo Super Admin puede gestionar configuración"
        )
    return current_user


@router.get("/status", response_model=SystemStatus)
async def get_system_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener estado de todas las integraciones."""
    service = ConfigurationService(db)
    status_dict = await service.get_system_status()
    return SystemStatus(**status_dict)


@router.get("/connectors/status")
async def get_connectors_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener estado detallado de todos los conectores."""
    statuses = []
    
    # Zoho
    try:
        config = await ConfigurationService(db).get_zoho_config()
        if config:
            async with ZohoRecruitConnector(db, config) as conn:
                connected, _ = await conn.test_connection()
                status = conn.get_status()
                statuses.append(ConnectorStatus(
                    name="Zoho Recruit",
                    connected=connected,
                    circuit_breaker_state=status["circuit_breaker"]["state"],
                    rate_limit_tokens=status["rate_limiter"]["tokens_available"]
                ))
    except Exception as e:
        statuses.append(ConnectorStatus(
            name="Zoho Recruit",
            connected=False,
            circuit_breaker_state="unknown",
            rate_limit_tokens=0
        ))
    
    # Odoo
    try:
        config = await ConfigurationService(db).get_odoo_config()
        if config:
            async with OdooConnector(db, config) as conn:
                connected, _ = await conn.test_connection()
                status = conn.get_status()
                statuses.append(ConnectorStatus(
                    name="Odoo",
                    connected=connected,
                    circuit_breaker_state=status["circuit_breaker"]["state"],
                    rate_limit_tokens=status["rate_limiter"]["tokens_available"]
                ))
    except Exception as e:
        statuses.append(ConnectorStatus(
            name="Odoo",
            connected=False,
            circuit_breaker_state="unknown",
            rate_limit_tokens=0
        ))
    
    return statuses


# ============== WHATSAPP CONFIG ==============

@router.get("/whatsapp", response_model=Optional[WhatsAppConfig])
async def get_whatsapp_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener configuración de WhatsApp Business API."""
    service = ConfigurationService(db)
    return await service.get_whatsapp_config()


@router.post("/whatsapp", response_model=MessageResponse)
async def set_whatsapp_config(
    config: WhatsAppConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Guardar configuración de WhatsApp Business API."""
    service = ConfigurationService(db)
    await service.set_whatsapp_config(config, updated_by=str(current_user.id))
    await db.commit()
    return MessageResponse(message="Configuración de WhatsApp guardada exitosamente")


@router.post("/whatsapp/test")
async def test_whatsapp_connection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Probar conexión con WhatsApp Business API."""
    service = ConfigurationService(db)
    success, message = await service.test_whatsapp_connection()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"success": True, "message": message}


# ============== ZOHO CONFIG ==============

@router.get("/zoho", response_model=Optional[ZohoConfig])
async def get_zoho_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener configuración de Zoho Recruit API."""
    service = ConfigurationService(db)
    return await service.get_zoho_config()


@router.post("/zoho", response_model=MessageResponse)
async def set_zoho_config(
    config: ZohoConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Guardar configuración de Zoho Recruit API."""
    service = ConfigurationService(db)
    await service.set_zoho_config(config, updated_by=str(current_user.id))
    await db.commit()
    return MessageResponse(message="Configuración de Zoho guardada exitosamente")


@router.post("/zoho/test")
async def test_zoho_connection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Probar conexión con Zoho Recruit."""
    service = ConfigurationService(db)
    success, message = await service.test_zoho_connection()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"success": True, "message": message}


@router.get("/zoho/auth-url")
async def get_zoho_auth_url(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener URL de autorización OAuth2 para Zoho."""
    service = ConfigurationService(db)
    config = await service.get_zoho_config()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay configuración de Zoho. Guarde client_id y client_secret primero."
        )
    
    async with ZohoRecruitConnector(db, config) as conn:
        auth_url = await conn.get_auth_url()
    
    return {"auth_url": auth_url}


@router.post("/zoho/callback")
async def zoho_oauth_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Callback de OAuth2 para Zoho."""
    params = dict(request.query_params)
    code = params.get("code")
    error = params.get("error")
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}"
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No authorization code received"
        )
    
    service = ConfigurationService(db)
    config = await service.get_zoho_config()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zoho config not found"
        )
    
    try:
        async with ZohoRecruitConnector(db, config) as conn:
            tokens = await conn.exchange_code_for_tokens(code)
            # Actualizar config con refresh token
            if "refresh_token" in tokens:
                config.refresh_token = tokens["refresh_token"]
                await service.set_zoho_config(config, updated_by=str(current_user.id))
                await db.commit()
        
        return {"success": True, "message": "Zoho OAuth completed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth exchange failed: {str(e)}"
        )


@router.post("/zoho/sync", response_model=SyncResponse)
async def sync_zoho(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Sincronizar datos desde Zoho Recruit."""
    service = SyncService()
    result = await service.sync_from_source(
        source=SyncSource.ZOHO,
        full_sync=request.full_sync,
        sync_jobs=request.sync_jobs,
        sync_candidates=request.sync_candidates
    )
    
    return SyncResponse(
        success=result.success,
        items_processed=result.items_processed,
        items_created=result.items_created,
        items_updated=result.items_updated,
        items_failed=result.items_failed,
        duration_ms=result.duration_ms,
        errors=result.errors,
        warnings=result.warnings
    )


# ============== ODOO CONFIG ==============

@router.get("/odoo", response_model=Optional[OdooConfig])
async def get_odoo_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener configuración de Odoo API."""
    service = ConfigurationService(db)
    return await service.get_odoo_config()


@router.post("/odoo", response_model=MessageResponse)
async def set_odoo_config(
    config: OdooConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Guardar configuración de Odoo API."""
    service = ConfigurationService(db)
    await service.set_odoo_config(config, updated_by=str(current_user.id))
    await db.commit()
    return MessageResponse(message="Configuración de Odoo guardada exitosamente")


@router.post("/odoo/test")
async def test_odoo_connection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Probar conexión con Odoo."""
    service = ConfigurationService(db)
    config = await service.get_odoo_config()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay configuración de Odoo"
        )
    
    try:
        async with OdooConnector(db, config) as conn:
            success, message = await conn.test_connection()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return {"success": True, "message": message}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection failed: {str(e)}"
        )


@router.post("/odoo/sync", response_model=SyncResponse)
async def sync_odoo(
    request: SyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Sincronizar datos desde Odoo."""
    service = SyncService()
    result = await service.sync_from_source(
        source=SyncSource.ODOO,
        full_sync=request.full_sync,
        sync_jobs=request.sync_jobs,
        sync_candidates=request.sync_candidates
    )
    
    return SyncResponse(
        success=result.success,
        items_processed=result.items_processed,
        items_created=result.items_created,
        items_updated=result.items_updated,
        items_failed=result.items_failed,
        duration_ms=result.duration_ms,
        errors=result.errors,
        warnings=result.warnings
    )


# ============== LINKEDIN CONFIG ==============

@router.get("/linkedin", response_model=Optional[LinkedInConfig])
async def get_linkedin_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener configuración de LinkedIn OAuth."""
    service = ConfigurationService(db)
    from app.schemas import ConfigCategory
    
    client_id = await service.get_value(ConfigCategory("linkedin"), "client_id")
    client_secret = await service.get_value(ConfigCategory("linkedin"), "client_secret")
    redirect_uri = await service.get_value(ConfigCategory("linkedin"), "redirect_uri")
    
    if client_id and client_secret:
        return LinkedInConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri or "http://localhost:8000/api/v1/config/linkedin/callback"
        )
    return None


@router.post("/linkedin", response_model=MessageResponse)
async def set_linkedin_config(
    config: LinkedInConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Guardar configuración de LinkedIn OAuth."""
    service = ConfigurationService(db)
    from app.schemas import ConfigCategory
    
    await service.set(ConfigCategory("linkedin"), "client_id", config.client_id, updated_by=str(current_user.id))
    await service.set(ConfigCategory("linkedin"), "client_secret", config.client_secret, updated_by=str(current_user.id))
    await service.set(ConfigCategory("linkedin"), "redirect_uri", config.redirect_uri, updated_by=str(current_user.id))
    await db.commit()
    
    return MessageResponse(message="Configuración de LinkedIn guardada exitosamente")


@router.post("/linkedin/test")
async def test_linkedin_connection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Probar conexión con LinkedIn."""
    service = ConfigurationService(db)
    from app.schemas import ConfigCategory
    
    client_id = await service.get_value(ConfigCategory("linkedin"), "client_id")
    client_secret = await service.get_value(ConfigCategory("linkedin"), "client_secret")
    
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay configuración de LinkedIn"
        )
    
    try:
        connector = LinkedInConnector(db, client_id, client_secret)
        authenticated = await connector.authenticate()
        
        if not authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LinkedIn authentication required. Please complete OAuth flow."
            )
        
        async with connector:
            success, message = await connector.test_connection()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection failed: {str(e)}"
        )


@router.get("/linkedin/auth-url")
async def get_linkedin_auth_url(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener URL de autorización OAuth2 para LinkedIn."""
    service = ConfigurationService(db)
    from app.schemas import ConfigCategory
    
    client_id = await service.get_value(ConfigCategory("linkedin"), "client_id")
    client_secret = await service.get_value(ConfigCategory("linkedin"), "client_secret")
    redirect_uri = await service.get_value(ConfigCategory("linkedin"), "redirect_uri")
    
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay configuración de LinkedIn. Guarde client_id y client_secret primero."
        )
    
    connector = LinkedInConnector(db, client_id, client_secret, redirect_uri or "http://localhost:8000/api/v1/config/linkedin/callback")
    auth_url = connector.get_auth_url(state=str(current_user.id))
    
    return {"auth_url": auth_url}


@router.post("/linkedin/callback")
async def linkedin_oauth_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Callback de OAuth2 para LinkedIn."""
    params = dict(request.query_params)
    code = params.get("code")
    error = params.get("error")
    error_description = params.get("error_description", "")
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error} - {error_description}"
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No authorization code received"
        )
    
    service = ConfigurationService(db)
    from app.schemas import ConfigCategory
    
    client_id = await service.get_value(ConfigCategory("linkedin"), "client_id")
    client_secret = await service.get_value(ConfigCategory("linkedin"), "client_secret")
    redirect_uri = await service.get_value(ConfigCategory("linkedin"), "redirect_uri")
    
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LinkedIn config not found"
        )
    
    try:
        connector = LinkedInConnector(db, client_id, client_secret, redirect_uri or "http://localhost:8000/api/v1/config/linkedin/callback")
        success, tokens = await connector.exchange_code_for_tokens(code)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=tokens.get("error", "Token exchange failed")
            )
        
        return {"success": True, "message": "LinkedIn OAuth completed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth exchange failed: {str(e)}"
        )


# ============== LLM CONFIG ==============

@router.get("/llm", response_model=Optional[LLMConfig])
async def get_llm_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener configuración de proveedor LLM."""
    service = ConfigurationService(db)
    return await service.get_llm_config()


@router.post("/llm", response_model=MessageResponse)
async def set_llm_config(
    config: LLMConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Guardar configuración de proveedor LLM."""
    service = ConfigurationService(db)
    await service.set_llm_config(config, updated_by=str(current_user.id))
    await db.commit()
    return MessageResponse(message="Configuración de LLM guardada exitosamente")


@router.post("/llm/test")
async def test_llm_connection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Probar conexión con proveedor LLM."""
    service = ConfigurationService(db)
    success, message = await service.test_llm_connection()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"success": True, "message": message}


# ============== EMAIL CONFIG ==============

@router.get("/email", response_model=Optional[EmailConfig])
async def get_email_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener configuración de Email."""
    service = ConfigurationService(db)
    return await service.get_email_config()


@router.post("/email", response_model=MessageResponse)
async def set_email_config(
    config: EmailConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Guardar configuración de Email."""
    service = ConfigurationService(db)
    await service.set_email_config(config, updated_by=str(current_user.id))
    await db.commit()
    return MessageResponse(message="Configuración de Email guardada exitosamente")


@router.post("/email/test")
async def test_email_connection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Probar conexión con servidor SMTP."""
    service = ConfigurationService(db)
    success, message = await service.test_email_connection()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"success": True, "message": message}


# ============== WEBHOOK RECEIVERS ==============

@router.post("/webhooks/zoho")
async def zoho_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Receiver para webhooks de Zoho Recruit.
    
    Zoho envía actualizaciones en tiempo real cuando:
    - Se crea/modifica/elimina un job
    - Se crea/modifica/elimina un candidato
    """
    payload = await request.body()
    headers = dict(request.headers)
    
    # Verificar token de webhook si está configurado
    # Zoho usa token en URL, no firma HMAC
    
    try:
        service = ConfigurationService(db)
        config = await service.get_zoho_config()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Zoho not configured"
            )
        
        async with ZohoRecruitConnector(db, config) as conn:
            handler = conn.get_webhook_handler()
            result = await handler.handle(payload, headers)
        
        return result
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Zoho webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.post("/webhooks/odoo")
async def odoo_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Receiver para webhooks de Odoo.
    
    Requiere configuración de automated actions en Odoo
    para enviar webhooks en eventos de hr.job y hr.applicant.
    """
    payload = await request.body()
    headers = dict(request.headers)
    
    # Verificar firma si hay secret configurado
    # signature = headers.get("X-Webhook-Signature")
    
    try:
        service = ConfigurationService(db)
        config = await service.get_odoo_config()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Odoo not configured"
            )
        
        async with OdooConnector(db, config) as conn:
            handler = conn.get_webhook_handler()
            result = await handler.handle(payload, headers)
        
        return result
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Odoo webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.get("/sync/logs")
async def get_sync_logs(
    source: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener logs de sincronización recientes."""
    service = SyncService()
    
    sync_source = SyncSource(source) if source else None
    logs = await service.get_sync_logs(source=sync_source, limit=limit)
    
    return {"logs": logs}


@router.get("/sync/health")
async def get_sync_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener estado de salud de sincronizaciones."""
    service = SyncService()
    health = await service.check_sync_health()
    return health


# ============== RAW CONFIG ENDPOINTS ==============

@router.get("/raw/{category}/{key}", response_model=ConfigurationResponse)
async def get_raw_config(
    category: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener configuración cruda (para casos especiales)."""
    from app.schemas import ConfigCategory
    
    service = ConfigurationService(db)
    config = await service.get(ConfigCategory(category), key)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración no encontrada"
        )
    
    # Enmascarar valor si es sensible
    value = None
    value_masked = None
    if config.is_encrypted:
        value_masked = "*" * 20  # Enmascarado
    else:
        value = config.value_encrypted
    
    return ConfigurationResponse(
        id=str(config.id),
        category=ConfigCategory(config.category),
        key=config.key,
        value=value,
        value_masked=value_masked,
        is_encrypted=config.is_encrypted,
        is_json=config.is_json,
        description=config.description,
        created_at=config.created_at,
        updated_at=config.updated_at,
        updated_by=str(config.updated_by) if config.updated_by else None
    )
