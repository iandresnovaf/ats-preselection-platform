"""
Sistema de caché para resultados de LLM.
Evita llamadas redundantes a OpenAI/Anthropic, reduciendo costos y mejorando performance.
"""
import json
import hashlib
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

import redis.asyncio as redis
from app.core.config import settings


class LLMCache:
    """
    Caché específica para resultados de LLM.
    
    Características:
    - Caché por contenido (hash del prompt + job)
    - TTL configurable (default: 24 horas)
    - Invalidación manual por force=True
    - Tracking de hits/misses
    """
    
    def __init__(
        self,
        redis_url: str = None,
        default_ttl: int = 86400,  # 24 horas
        prefix: str = "llm_cache"
    ):
        self.redis_url = redis_url or settings.REDIS_URL
        self.default_ttl = default_ttl
        self.prefix = prefix
        self._redis: Optional[redis.Redis] = None
    
    async def get_redis(self) -> redis.Redis:
        """Obtiene o crea conexión Redis."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    def _generate_key(
        self,
        candidate_data: Dict[str, Any],
        job_data: Dict[str, Any],
        provider: str = "openai",
        model: str = "gpt-4o-mini"
    ) -> str:
        """
        Genera una key de caché única basada en el contenido.
        
        El hash se calcula sobre:
        - Datos relevantes del candidato (skills, experience, education)
        - Descripción del job
        - Provider y modelo (diferentes modelos = diferentes resultados)
        """
        # Extraer datos relevantes del candidato
        candidate_hash_data = {
            "skills": sorted(candidate_data.get("extracted_skills", [])),
            "experience": candidate_data.get("extracted_experience", []),
            "education": candidate_data.get("extracted_education", []),
            "raw_data": candidate_data.get("raw_data", {})
        }
        
        # Datos del job
        job_hash_data = {
            "title": job_data.get("title"),
            "description": job_data.get("description"),
            "department": job_data.get("department"),
            "seniority": job_data.get("seniority")
        }
        
        # Combinar y hashear
        cache_data = {
            "candidate": candidate_hash_data,
            "job": job_hash_data,
            "provider": provider,
            "model": model,
            "version": "v1.0"  # Para invalidar caché cuando cambie la lógica
        }
        
        data_str = json.dumps(cache_data, sort_keys=True, default=str)
        content_hash = hashlib.sha256(data_str.encode()).hexdigest()[:32]
        
        return f"{self.prefix}:{content_hash}"
    
    async def get(
        self,
        candidate_data: Dict[str, Any],
        job_data: Dict[str, Any],
        provider: str = "openai",
        model: str = "gpt-4o-mini"
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene un resultado de caché.
        
        Returns:
            Dict con el resultado cacheado o None si no existe
        """
        try:
            r = await self.get_redis()
            key = self._generate_key(candidate_data, job_data, provider, model)
            
            cached = await r.get(key)
            if cached:
                data = json.loads(cached)
                data["_cached"] = True
                data["_cache_key"] = key
                return data
            
            return None
            
        except Exception as e:
            # Si Redis falla, retornar None (fail open)
            return None
    
    async def set(
        self,
        candidate_data: Dict[str, Any],
        job_data: Dict[str, Any],
        result: Dict[str, Any],
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        ttl: int = None
    ) -> bool:
        """
        Guarda un resultado en caché.
        
        Returns:
            True si se guardó correctamente
        """
        try:
            r = await self.get_redis()
            key = self._generate_key(candidate_data, job_data, provider, model)
            
            # Agregar metadata de caché
            result_to_cache = result.copy()
            result_to_cache["_cached_at"] = datetime.utcnow().isoformat()
            result_to_cache["_cache_ttl"] = ttl or self.default_ttl
            
            await r.setex(
                key,
                ttl or self.default_ttl,
                json.dumps(result_to_cache, default=str)
            )
            
            return True
            
        except Exception as e:
            # Si Redis falla, continuar sin caché
            return False
    
    async def invalidate(
        self,
        candidate_data: Dict[str, Any],
        job_data: Dict[str, Any],
        provider: str = "openai",
        model: str = "gpt-4o-mini"
    ) -> bool:
        """
        Invalida una entrada de caché específica.
        """
        try:
            r = await self.get_redis()
            key = self._generate_key(candidate_data, job_data, provider, model)
            await r.delete(key)
            return True
        except Exception:
            return False
    
    async def invalidate_all(self, pattern: str = None) -> int:
        """
        Invalida todas las entradas de caché de LLM.
        
        Args:
            pattern: Patrón opcional para invalidación selectiva
        
        Returns:
            Número de entradas eliminadas
        """
        try:
            r = await self.get_redis()
            pattern = pattern or f"{self.prefix}:*"
            
            # Buscar keys
            keys = []
            async for key in r.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await r.delete(*keys)
            
            return len(keys)
            
        except Exception:
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso de caché.
        """
        try:
            r = await self.get_redis()
            
            # Contar keys de caché
            pattern = f"{self.prefix}:*"
            count = 0
            async for _ in r.scan_iter(match=pattern):
                count += 1
            
            return {
                "cached_entries": count,
                "prefix": self.prefix,
                "default_ttl": self.default_ttl
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "cached_entries": 0
            }


# Singleton
_llm_cache: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    """Obtiene instancia singleton del caché LLM."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
    return _llm_cache


# Función de conveniencia para usar en servicios
async def get_cached_evaluation(
    candidate_data: Dict[str, Any],
    job_data: Dict[str, Any],
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    force_refresh: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Obtiene una evaluación cacheada.
    
    Usage:
        cached = await get_cached_evaluation(candidate_data, job_data)
        if cached and not force_refresh:
            return cached
        
        # Generar nueva evaluación
        result = await llm_client.evaluate(candidate_data, job_data)
        await cache_evaluation(candidate_data, job_data, result)
        return result
    """
    if force_refresh:
        return None
    
    cache = get_llm_cache()
    return await cache.get(candidate_data, job_data, provider, model)


async def cache_evaluation(
    candidate_data: Dict[str, Any],
    job_data: Dict[str, Any],
    result: Dict[str, Any],
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    ttl: int = None
) -> bool:
    """
    Guarda una evaluación en caché.
    """
    cache = get_llm_cache()
    return await cache.set(candidate_data, job_data, result, provider, model, ttl)
