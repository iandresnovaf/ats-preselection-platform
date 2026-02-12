"""Sistema de caching con Redis."""
import json
import redis.asyncio as redis
from typing import Optional, Any, Union
from datetime import datetime, timedelta

from app.core.config import settings


class Cache:
    """Cliente de cache Redis para la aplicación."""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Obtener o crear conexión Redis lazy."""
        if self._redis is None:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor del cache."""
        try:
            r = await self._get_redis()
            value = await r.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception:
            # Fallback: si Redis falla, retornar None (cache miss)
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = 300,
        nx: bool = False
    ) -> bool:
        """
        Guardar valor en cache.
        
        Args:
            key: Clave del cache
            value: Valor a guardar (debe ser JSON serializable)
            ttl: Tiempo de vida en segundos (default: 5 minutos)
            nx: Solo setear si no existe
        """
        try:
            r = await self._get_redis()
            serialized = json.dumps(value, default=str)
            await r.set(key, serialized, ex=ttl, nx=nx)
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Eliminar una clave del cache."""
        try:
            r = await self._get_redis()
            await r.delete(key)
            return True
        except Exception:
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Eliminar todas las claves que coincidan con el patrón."""
        try:
            r = await self._get_redis()
            keys = await r.keys(pattern)
            if keys:
                return await r.delete(*keys)
            return 0
        except Exception:
            return 0
    
    async def exists(self, key: str) -> bool:
        """Verificar si una clave existe en el cache."""
        try:
            r = await self._get_redis()
            return await r.exists(key) > 0
        except Exception:
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Incrementar contador atómico."""
        try:
            r = await self._get_redis()
            return await r.incrby(key, amount)
        except Exception:
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Setear tiempo de expiración a una clave existente."""
        try:
            r = await self._get_redis()
            return await r.expire(key, seconds)
        except Exception:
            return False
    
    async def ttl(self, key: str) -> int:
        """Obtener tiempo restante de vida de una clave."""
        try:
            r = await self._get_redis()
            return await r.ttl(key)
        except Exception:
            return -2
    
    async def close(self):
        """Cerrar conexión Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# Instancia global del cache
cache = Cache()


# Helper decorators para uso común
def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator para cachear resultados de funciones async.
    
    Usage:
        @cached(ttl=600, key_prefix="user")
        async def get_user(user_id: str):
            return await db.get_user(user_id)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generar key basado en función y argumentos
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Intentar obtener del cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Ejecutar función y cachear resultado
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator


# Helpers para invalidación de cache
async def invalidate_config_cache(category: str, key: str):
    """Invalidar cache de configuración específica."""
    await cache.delete(f"config:{category}:{key}")


async def invalidate_job_cache(job_id: str = None):
    """Invalidar cache de jobs."""
    if job_id:
        await cache.delete(f"job:{job_id}")
    await cache.delete_pattern("jobs:list:*")


async def invalidate_candidate_cache(candidate_id: str = None):
    """Invalidar cache de candidatos."""
    if candidate_id:
        await cache.delete(f"candidate:{candidate_id}")
    await cache.delete_pattern("candidates:list:*")
