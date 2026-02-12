"""
Decoradores y utilidades para rate limiting específico de endpoints de IA.
Este módulo implementa rate limiting para endpoints que consumen recursos externos (LLM).
"""
import time
import hashlib
import json
from typing import Optional, Callable
from functools import wraps

from fastapi import Request, HTTPException, status
import redis.asyncio as redis

from app.core.config import settings
from app.core.security_logging import SecurityLogger


security_logger = SecurityLogger()


class LLMRateLimiter:
    """
    Rate limiter específico para endpoints de LLM.
    
    Características:
    - Limita requests por usuario
    - Limita requests por IP
    - Tracking de costos estimados
    - Alertas de uso anómalo
    """
    
    def __init__(
        self,
        requests_per_minute: int = 5,
        requests_per_hour: int = 50,
        daily_limit: int = 200,
        redis_url: str = None
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.daily_limit = daily_limit
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None
    
    async def get_redis(self) -> redis.Redis:
        """Obtiene o crea conexión Redis."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    def get_key(self, identifier: str, window: str) -> str:
        """Genera key de Redis para rate limiting."""
        return f"llm_ratelimit:{window}:{identifier}"
    
    async def check_rate_limit(self, user_id: str, ip_address: str) -> dict:
        """
        Verifica todos los límites de rate.
        
        Returns:
            dict con información del rate limit
        """
        r = await self.get_redis()
        
        # Keys para diferentes ventanas
        user_key_minute = self.get_key(user_id, "minute")
        user_key_hour = self.get_key(user_id, "hour")
        user_key_day = self.get_key(user_id, "day")
        ip_key_minute = self.get_key(ip_address, "ip_minute")
        
        current_time = int(time.time())
        
        # Pipeline para operaciones atómicas
        pipe = r.pipeline()
        
        # Incrementar contadores
        pipe.incr(user_key_minute)
        pipe.incr(user_key_hour)
        pipe.incr(user_key_day)
        pipe.incr(ip_key_minute)
        
        # Setear TTL en primer request
        pipe.expire(user_key_minute, 60, nx=True)
        pipe.expire(user_key_hour, 3600, nx=True)
        pipe.expire(user_key_day, 86400, nx=True)
        pipe.expire(ip_key_minute, 60, nx=True)
        
        results = await pipe.execute()
        
        # Contadores actuales
        minute_count = results[0]
        hour_count = results[1]
        day_count = results[2]
        ip_minute_count = results[3]
        
        # Verificar límites
        limits = {
            "allowed": True,
            "limits": {
                "minute": {"current": minute_count, "limit": self.requests_per_minute, "remaining": max(0, self.requests_per_minute - minute_count)},
                "hour": {"current": hour_count, "limit": self.requests_per_hour, "remaining": max(0, self.requests_per_hour - hour_count)},
                "day": {"current": day_count, "limit": self.daily_limit, "remaining": max(0, self.daily_limit - day_count)},
                "ip_minute": {"current": ip_minute_count, "limit": self.requests_per_minute * 2, "remaining": max(0, self.requests_per_minute * 2 - ip_minute_count)}
            },
            "retry_after": 0
        }
        
        # Verificar violaciones
        if minute_count > self.requests_per_minute:
            limits["allowed"] = False
            limits["violated"] = "minute"
            limits["retry_after"] = 60
        elif hour_count > self.requests_per_hour:
            limits["allowed"] = False
            limits["violated"] = "hour"
            limits["retry_after"] = 3600 - (current_time % 3600)
        elif day_count > self.daily_limit:
            limits["allowed"] = False
            limits["violated"] = "day"
            limits["retry_after"] = 86400 - (current_time % 86400)
        elif ip_minute_count > self.requests_per_minute * 2:
            limits["allowed"] = False
            limits["violated"] = "ip_minute"
            limits["retry_after"] = 60
        
        return limits
    
    async def track_cost(self, user_id: str, estimated_cost: float = 0.01):
        """Tracking de costos estimados por usuario."""
        r = await self.get_redis()
        
        key = f"llm_cost:{user_id}:{datetime.now().strftime('%Y-%m-%d')}"
        await r.incrbyfloat(key, estimated_cost)
        await r.expire(key, 86400 * 30)  # Mantener por 30 días


# Singleton
def get_llm_rate_limiter() -> LLMRateLimiter:
    return LLMRateLimiter()


def llm_rate_limit(
    requests_per_minute: int = 5,
    requests_per_hour: int = 50,
    daily_limit: int = 200
):
    """
    Decorador para rate limiting en endpoints de LLM.
    
    Args:
        requests_per_minute: Máximo de requests por minuto por usuario
        requests_per_hour: Máximo de requests por hora por usuario
        daily_limit: Máximo de requests por día por usuario
    
    Usage:
        @router.post("/{candidate_id}/evaluate")
        @llm_rate_limit(requests_per_minute=5, requests_per_hour=50)
        async def evaluate_candidate(...):
            ...
    """
    limiter = LLMRateLimiter(
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        daily_limit=daily_limit
    )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extraer request de kwargs o args
            request: Optional[Request] = kwargs.get('request')
            if not request and args:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            # Extraer user_id del contexto
            user_id = None
            current_user = kwargs.get('current_user')
            if current_user:
                user_id = str(current_user.id)
            
            if not user_id:
                user_id = "anonymous"
            
            # Obtener IP
            ip_address = "unknown"
            if request:
                forwarded = request.headers.get("X-Forwarded-For")
                if forwarded:
                    ip_address = forwarded.split(",")[0].strip()
                elif request.client:
                    ip_address = request.client.host
            
            # Verificar rate limit
            limits = await limiter.check_rate_limit(user_id, ip_address)
            
            if not limits["allowed"]:
                await security_logger.log_rate_limit_hit(
                    request,
                    f"llm_{limits['violated']}",
                    limits["retry_after"]
                )
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": f"Has excedido el límite de {limits['violated']}. "
                                   f"Intenta de nuevo en {limits['retry_after']} segundos.",
                        "retry_after": limits["retry_after"],
                        "limits": limits["limits"]
                    },
                    headers={"Retry-After": str(limits["retry_after"])}
                )
            
            # Ejecutar función
            response = await func(*args, **kwargs)
            
            return response
        
        return wrapper
    return decorator


# Decorador específico para evaluaciones
def evaluation_rate_limit(func: Callable) -> Callable:
    """
    Decorador simplificado para endpoint de evaluación.
    Límites: 5/min, 50/hour, 200/day
    """
    return llm_rate_limit(
        requests_per_minute=5,
        requests_per_hour=50,
        daily_limit=200
    )(func)
