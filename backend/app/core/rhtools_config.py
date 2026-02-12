"""Feature flags y configuración de RHTools."""
from functools import lru_cache
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import async_session_maker
from app.models import Configuration

# Constante para el provider
ATS_PROVIDER_KEY = "ats_provider"
ATS_PROVIDER_CATEGORY = "general"


class ATSProvider:
    """Proveedores de ATS soportados."""
    ZOHO = "zoho"
    ODOO = "odoo"
    RHTOOLS = "rhtools"


async def get_ats_provider() -> Optional[str]:
    """
    Obtener el proveedor de ATS configurado.
    
    Returns:
        Nombre del proveedor (zoho, odoo, rhtools) o None si no está configurado
    """
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Configuration).where(
                    Configuration.category == ATS_PROVIDER_CATEGORY,
                    Configuration.key == ATS_PROVIDER_KEY
                )
            )
            config = result.scalar_one_or_none()
            
            if config:
                # Si está encriptado, necesitaríamos desencriptarlo
                # pero el valor del provider no es sensible, así que no debería estar encriptado
                return config.value_encrypted if not config.is_encrypted else None
            return None
    except Exception:
        # Si hay error, retornamos None (feature desactivado)
        return None


def is_rhtools_enabled_sync() -> bool:
    """
    Verificación síncrona para casos donde no hay async context.
    Usar con precaución - preferir is_rhtools_enabled() async cuando sea posible.
    """
    # Por ahora, solo verificamos variable de entorno como fallback
    return getattr(settings, 'ATS_PROVIDER', '').lower() == 'rhtools'


async def is_rhtools_enabled() -> bool:
    """
    Verificar si RHTools está habilitado como proveedor de ATS.
    
    Returns:
        True si RHTools es el ATS configurado
    """
    provider = await get_ats_provider()
    if provider and provider.lower() == ATSProvider.RHTOOLS:
        return True
    
    # Fallback a variable de entorno
    return is_rhtools_enabled_sync()


async def set_ats_provider(provider: str, db: AsyncSession) -> bool:
    """
    Configurar el proveedor de ATS.
    
    Args:
        provider: Nombre del proveedor (zoho, odoo, rhtools)
        db: Sesión de base de datos
        
    Returns:
        True si se configuró exitosamente
    """
    from app.schemas import ConfigCategory
    
    # Validar provider
    valid_providers = [ATSProvider.ZOHO, ATSProvider.ODOO, ATSProvider.RHTOOLS]
    if provider.lower() not in valid_providers:
        raise ValueError(f"Provider inválido. Debe ser uno de: {', '.join(valid_providers)}")
    
    # Buscar o crear configuración
    result = await db.execute(
        select(Configuration).where(
            Configuration.category == ATS_PROVIDER_CATEGORY,
            Configuration.key == ATS_PROVIDER_KEY
        )
    )
    config = result.scalar_one_or_none()
    
    if config:
        config.value_encrypted = provider.lower()
        config.is_encrypted = False
    else:
        config = Configuration(
            category=ATS_PROVIDER_CATEGORY,
            key=ATS_PROVIDER_KEY,
            value_encrypted=provider.lower(),
            is_encrypted=False,
            description="Proveedor de ATS activo (zoho, odoo, rhtools)"
        )
        db.add(config)
    
    await db.flush()
    return True
