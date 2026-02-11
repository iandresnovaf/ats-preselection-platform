"""API endpoints para configuración del sistema."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, UserRole
from app.schemas import (
    ConfigurationCreate,
    ConfigurationUpdate,
    ConfigurationResponse,
    WhatsAppConfig,
    ZohoConfig,
    LLMConfig,
    EmailConfig,
    SystemStatus,
    MessageResponse,
)
from app.services.configuration_service import ConfigurationService

router = APIRouter(prefix="/config", tags=["Configuration"])


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


# ============== RAW CONFIG ENDPOINTS ==============

@router.get("/raw/{category}/{key}", response_model=ConfigurationResponse)
async def get_raw_config(
    category: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obtener configuración cruda (para casos especiales)."""
    from app.models import ConfigCategory
    
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
