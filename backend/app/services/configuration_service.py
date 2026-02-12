"""Servicio de gestión de configuraciones."""
from typing import Optional, List, Dict, Any, Type
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import Configuration
from app.schemas import ConfigCategory
from app.schemas import (
    ConfigurationCreate, 
    ConfigurationUpdate,
    ConfigurationResponse,
    WhatsAppConfig,
    ZohoConfig,
    LLMConfig,
    EmailConfig,
)
from app.core.security import encrypt_value, decrypt_value
from app.core.cache import cache


class ConfigurationService:
    """Servicio para gestionar configuraciones del sistema."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_config(self, category: str, key: str) -> Optional[str]:
        """
        Obtener configuración con cache.
        
        Args:
            category: Categoría de la configuración
            key: Clave de la configuración
            
        Returns:
            Valor descifrado de la configuración o None
        """
        cache_key = f"config:{category}:{key}"
        
        # Intentar obtener del cache
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Obtener de base de datos
        value = await self._get_from_db(category, key)
        
        # Guardar en cache (5 minutos por defecto)
        if value is not None:
            await cache.set(cache_key, value, ttl=300)
        
        return value
    
    async def _get_from_db(self, category: str, key: str) -> Optional[str]:
        """Obtener valor de configuración desde la base de datos."""
        try:
            # Convertir string a ConfigCategory enum si es necesario
            cat_value = category.value if hasattr(category, 'value') else category
            
            result = await self.db.execute(
                select(Configuration).where(
                    and_(
                        Configuration.category == cat_value,
                        Configuration.key == key
                    )
                )
            )
            config = result.scalar_one_or_none()
            
            if not config:
                return None
            
            if config.is_encrypted:
                return decrypt_value(config.value_encrypted)
            return config.value_encrypted
            
        except Exception:
            return None
    
    async def invalidate_config_cache(self, category: str, key: str):
        """Invalidar cache de una configuración específica."""
        await cache.delete(f"config:{category}:{key}")
    
    async def get(self, category: ConfigCategory, key: str) -> Optional[Configuration]:
        """Obtener una configuración por categoría y clave."""
        result = await self.db.execute(
            select(Configuration).where(
                and_(
                    Configuration.category == category.value,
                    Configuration.key == key
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_value(self, category: ConfigCategory, key: str) -> Optional[str]:
        """Obtener el valor descifrado de una configuración."""
        config = await self.get(category, key)
        if not config:
            return None
        
        if config.is_encrypted:
            return decrypt_value(config.value_encrypted)
        return config.value_encrypted
    
    async def get_json_value(self, category: ConfigCategory, key: str) -> Optional[Dict]:
        """Obtener valor JSON parseado."""
        value = await self.get_value(category, key)
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    
    async def set(
        self,
        category: ConfigCategory,
        key: str,
        value: str,
        description: Optional[str] = None,
        is_encrypted: bool = True,
        is_json: bool = False,
        updated_by: Optional[str] = None
    ) -> Configuration:
        """Crear o actualizar una configuración."""
        # Buscar existente
        existing = await self.get(category, key)

        if existing:
            # Actualizar
            if is_encrypted:
                existing.value_encrypted = encrypt_value(value)
            else:
                existing.value_encrypted = value
            existing.is_encrypted = is_encrypted
            existing.is_json = is_json
            if description:
                existing.description = description
            if updated_by:
                existing.updated_by = updated_by
            await self.db.flush()
            # Invalidar cache después de actualizar
            await self.invalidate_config_cache(category.value, key)
            return existing
        else:
            # Crear nueva
            if is_encrypted:
                encrypted_value = encrypt_value(value)
            else:
                encrypted_value = value

            config = Configuration(
                category=category.value,
                key=key,
                value_encrypted=encrypted_value,
                is_encrypted=is_encrypted,
                is_json=is_json,
                description=description,
                updated_by=updated_by
            )
            self.db.add(config)
            await self.db.flush()
            return config
    
    async def set_json(
        self,
        category: ConfigCategory,
        key: str,
        value: Dict[Any, Any],
        **kwargs
    ) -> Configuration:
        """Guardar valor como JSON."""
        return await self.set(
            category=category,
            key=key,
            value=json.dumps(value),
            is_json=True,
            **kwargs
        )
    
    async def get_all_by_category(self, category: ConfigCategory) -> List[Configuration]:
        """Obtener todas las configuraciones de una categoría."""
        result = await self.db.execute(
            select(Configuration).where(Configuration.category == category.value)
        )
        return result.scalars().all()
    
    async def delete(self, category: ConfigCategory, key: str) -> bool:
        """Eliminar una configuración."""
        config = await self.get(category, key)
        if config:
            await self.db.delete(config)
            await self.db.flush()
            # Invalidar cache después de eliminar
            await self.invalidate_config_cache(category.value, key)
            return True
        return False
    
    # ============ HELPERS PARA CONFIGS ESPECÍFICAS ============
    
    async def get_whatsapp_config(self) -> Optional[WhatsAppConfig]:
        """Obtener configuración de WhatsApp."""
        data = await self.get_json_value(ConfigCategory.WHATSAPP, "config")
        if data:
            return WhatsAppConfig(**data)
        return None
    
    async def set_whatsapp_config(
        self, 
        config: WhatsAppConfig, 
        updated_by: Optional[str] = None
    ) -> Configuration:
        """Guardar configuración de WhatsApp."""
        return await self.set_json(
            category=ConfigCategory.WHATSAPP,
            key="config",
            value=config.model_dump(),
            description="Configuración de WhatsApp Business API",
            updated_by=updated_by
        )
    
    async def get_zoho_config(self) -> Optional[ZohoConfig]:
        """Obtener configuración de Zoho."""
        data = await self.get_json_value(ConfigCategory.ZOHO, "config")
        if data:
            return ZohoConfig(**data)
        return None
    
    async def set_zoho_config(
        self, 
        config: ZohoConfig, 
        updated_by: Optional[str] = None
    ) -> Configuration:
        """Guardar configuración de Zoho."""
        return await self.set_json(
            category=ConfigCategory.ZOHO,
            key="config",
            value=config.model_dump(),
            description="Configuración de Zoho Recruit API",
            updated_by=updated_by
        )
    
    async def get_llm_config(self) -> Optional[LLMConfig]:
        """Obtener configuración de LLM."""
        data = await self.get_json_value(ConfigCategory.LLM, "config")
        if data:
            return LLMConfig(**data)
        return None
    
    async def set_llm_config(
        self, 
        config: LLMConfig, 
        updated_by: Optional[str] = None
    ) -> Configuration:
        """Guardar configuración de LLM."""
        return await self.set_json(
            category=ConfigCategory.LLM,
            key="config",
            value=config.model_dump(),
            description="Configuración de proveedor LLM",
            updated_by=updated_by
        )
    
    async def get_email_config(self) -> Optional[EmailConfig]:
        """Obtener configuración de Email."""
        data = await self.get_json_value(ConfigCategory.EMAIL, "config")
        if data:
            return EmailConfig(**data)
        return None
    
    async def set_email_config(
        self, 
        config: EmailConfig, 
        updated_by: Optional[str] = None
    ) -> Configuration:
        """Guardar configuración de Email."""
        return await self.set_json(
            category=ConfigCategory.EMAIL,
            key="config",
            value=config.model_dump(),
            description="Configuración de servidor SMTP/Email",
            updated_by=updated_by
        )
    
    async def test_whatsapp_connection(self) -> tuple[bool, str]:
        """Probar conexión con WhatsApp Business API."""
        config = await self.get_whatsapp_config()
        if not config:
            return False, "No hay configuración de WhatsApp"
        
        try:
            # TODO: Implementar test real con Meta API
            # Por ahora solo validamos que tengamos los campos necesarios
            if not config.access_token or not config.phone_number_id:
                return False, "Faltan campos requeridos: access_token, phone_number_id"
            
            # Aquí iría la llamada real a la API de Meta
            # async with httpx.AsyncClient() as client:
            #     response = await client.get(...)
            
            return True, "Configuración válida (test real pendiente)"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    async def test_zoho_connection(self) -> tuple[bool, str]:
        """Probar conexión con Zoho Recruit."""
        config = await self.get_zoho_config()
        if not config:
            return False, "No hay configuración de Zoho"
        
        try:
            if not config.client_id or not config.client_secret:
                return False, "Faltan campos requeridos: client_id, client_secret"
            
            # TODO: Implementar test real con Zoho API
            return True, "Configuración válida (test real pendiente)"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    async def test_llm_connection(self) -> tuple[bool, str]:
        """Probar conexión con proveedor LLM."""
        config = await self.get_llm_config()
        if not config:
            return False, "No hay configuración de LLM"
        
        try:
            if not config.api_key:
                return False, "Falta API key"
            
            # TODO: Implementar test real con OpenAI/Anthropic
            return True, "Configuración válida (test real pendiente)"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    async def test_email_connection(self) -> tuple[bool, str]:
        """Probar conexión con servidor SMTP."""
        config = await self.get_email_config()
        if not config:
            return False, "No hay configuración de Email"
        
        try:
            if not config.smtp_host or not config.smtp_user:
                return False, "Faltan campos requeridos: smtp_host, smtp_user"
            
            # TODO: Implementar test real con SMTP
            return True, "Configuración válida (test real pendiente)"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Obtener estado de todas las integraciones."""
        from app.core.database import engine
        from app.core.config import settings
        import redis.asyncio as redis
        
        status = {
            "database": False,
            "redis": False,
            "whatsapp": None,
            "zoho": None,
            "llm": None,
            "email": None,
        }
        
        # Test database
        try:
            async with engine.connect() as conn:
                await conn.execute(select(1))
                status["database"] = True
        except Exception:
            pass
        
        # Test Redis
        try:
            r = redis.from_url(settings.REDIS_URL)
            await r.ping()
            status["redis"] = True
            await r.close()
        except Exception:
            pass
        
        # Test integrations (solo si hay config)
        if await self.get_whatsapp_config():
            ok, _ = await self.test_whatsapp_connection()
            status["whatsapp"] = ok
        
        if await self.get_zoho_config():
            ok, _ = await self.test_zoho_connection()
            status["zoho"] = ok
        
        if await self.get_llm_config():
            ok, _ = await self.test_llm_connection()
            status["llm"] = ok
        
        if await self.get_email_config():
            ok, _ = await self.test_email_connection()
            status["email"] = ok
        
        return status
