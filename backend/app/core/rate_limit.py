"""Rate limiting middleware usando Redis."""
import time
from typing import Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware para rate limiting basado en IP."""
    
    def __init__(
        self,
        app,
        redis_url: str = None,
        requests_per_minute: int = 60,
        auth_requests_per_minute: int = 5,
    ):
        super().__init__(app)
        self.redis_url = redis_url or settings.REDIS_URL
        self.requests_per_minute = requests_per_minute
        self.auth_requests_per_minute = auth_requests_per_minute
        self._redis: Optional[redis.Redis] = None
    
    async def get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    def get_client_ip(self, request: Request) -> str:
        """Obtiene la IP real del cliente considerando proxies."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def is_auth_endpoint(self, path: str) -> bool:
        """Verifica si es un endpoint de autenticación."""
        auth_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
        ]
        return any(path.startswith(p) for p in auth_paths)
    
    async def dispatch(self, request: Request, call_next):
        # Solo aplicar rate limiting a endpoints específicos
        if not self.is_auth_endpoint(request.url.path):
            return await call_next(request)
        
        client_ip = self.get_client_ip(request)
        path = request.url.path
        
        # Key específica por IP y endpoint
        key = f"ratelimit:{client_ip}:{path}"
        
        try:
            r = await self.get_redis()
            
            # Window de 1 minuto
            window = 60
            limit = self.auth_requests_per_minute
            
            # Incrementar contador
            current = await r.incr(key)
            
            # Setear TTL en el primer request
            if current == 1:
                await r.expire(key, window)
            
            # Verificar límite
            ttl = await r.ttl(key)
            
            if current > limit:
                # Retornar respuesta 429 directamente en lugar de lanzar excepción
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Demasiadas solicitudes. Intenta de nuevo en {ttl} segundos.",
                        "retry_after": ttl
                    },
                    headers={
                        "Retry-After": str(ttl),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time() + ttl))
                    }
                )
            
            # Agregar headers de rate limit
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current))
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + ttl))
            
            return response
            
        except Exception:
            # Si Redis falla, permitir el request (fail open)
            return await call_next(request)
