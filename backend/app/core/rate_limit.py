"""Rate limiting middleware mejorado con protección por usuario e IP."""
import time
import hashlib
from datetime import datetime
from typing import Optional, Dict, Tuple
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware para rate limiting basado en IP y usuario."""
    
    def __init__(
        self,
        app,
        redis_url: str = None,
        requests_per_minute: int = 60,
        auth_requests_per_minute: int = 5,
        login_requests_per_minute: int = 3,  # Más restrictivo para login
        password_reset_per_hour: int = 1,    # 1 intento por hora
        candidates_post_per_minute: int = 10, # 10 candidatos por minuto
        user_requests_per_minute: int = 100,  # Límite por usuario autenticado
    ):
        super().__init__(app)
        self.redis_url = redis_url or settings.REDIS_URL
        self.requests_per_minute = requests_per_minute
        self.auth_requests_per_minute = auth_requests_per_minute
        self.login_requests_per_minute = login_requests_per_minute
        self.password_reset_per_hour = password_reset_per_hour
        self.candidates_post_per_minute = candidates_post_per_minute
        self.user_requests_per_minute = user_requests_per_minute
        self._redis: Optional[redis.Redis] = None
        
        # Tracking de IPs sospechosas para protección contra enumeration
        self._suspicious_ips: Dict[str, Dict] = {}
    
    async def get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    def get_client_ip(self, request: Request) -> str:
        """Obtiene la IP real del cliente considerando proxies."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"
    
    def get_user_id(self, request: Request) -> Optional[str]:
        """Extrae user_id del token JWT si existe."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Extraer sub del token sin verificar (solo para rate limiting)
            try:
                import jwt
                from jwt.exceptions import PyJWTError
                token = auth_header.split(" ")[1]
                payload = jwt.decode(
                    token, 
                    settings.SECRET_KEY, 
                    algorithms=[settings.ALGORITHM],
                    options={"verify_exp": False}  # No verificar exp para rate limit
                )
                return payload.get("sub")
            except Exception:
                pass
        return None
    
    def get_identifier(self, request: Request) -> Tuple[str, Optional[str]]:
        """Obtiene identificador único (IP + user_id si está autenticado)."""
        client_ip = self.get_client_ip(request)
        user_id = self.get_user_id(request)
        
        # Si hay user_id, usar combinación de IP + user_id
        if user_id:
            # Hash para no exponer user_id directamente
            identifier = hashlib.sha256(f"{client_ip}:{user_id}".encode()).hexdigest()[:16]
            return identifier, user_id
        
        return client_ip, None
    
    def is_auth_endpoint(self, path: str) -> bool:
        """Verifica si es un endpoint de autenticación."""
        auth_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/login/mfa",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
        ]
        return any(path.startswith(p) for p in auth_paths)
    
    def is_login_endpoint(self, path: str) -> bool:
        """Verifica si es el endpoint de login (más restrictivo)."""
        return path.startswith("/api/v1/auth/login")
    
    def is_password_reset_endpoint(self, path: str) -> bool:
        """Verifica si es endpoint de reset password (muy restrictivo)."""
        return path.startswith("/api/v1/auth/forgot-password") or path.startswith("/api/v1/auth/reset-password")
    
    def is_candidates_post_endpoint(self, path: str, method: str) -> bool:
        """Verifica si es POST a /api/v1/candidates (rate limit específico)."""
        return method == "POST" and path.startswith("/api/v1/candidates")
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        limit: int, 
        window: int = 60,
        key_prefix: str = "ratelimit"
    ) -> Tuple[bool, int, int, int]:
        """
        Verifica si se ha excedido el rate limit.
        Returns: (allowed, current_count, ttl, remaining)
        """
        try:
            r = await self.get_redis()
            key = f"{key_prefix}:{identifier}"
            
            # Incrementar contador
            current = await r.incr(key)
            
            # Setear TTL en el primer request
            if current == 1:
                await r.expire(key, window)
            
            ttl = await r.ttl(key)
            remaining = max(0, limit - current)
            allowed = current <= limit
            
            return allowed, current, ttl, remaining
            
        except Exception:
            # Si Redis falla, permitir el request (fail open)
            return True, 0, 0, limit
    
    async def check_enumeration_protection(self, ip: str, identifier: str) -> bool:
        """
        Protección contra user enumeration attacks.
        Detecta múltiples intentos de login con diferentes usuarios desde la misma IP.
        """
        try:
            r = await self.get_redis()
            key = f"enum_protection:{ip}"
            
            # Contar intentos de login únicos por IP
            current = await r.incr(key)
            
            if current == 1:
                await r.expire(key, 300)  # Ventana de 5 minutos
            
            # Si más de 10 intentos de login en 5 minutos desde la misma IP
            if current > 10:
                # Bloquear IP temporalmente
                block_key = f"blocked_ip:{ip}"
                await r.setex(block_key, 900, "blocked")  # 15 minutos
                return False
            
            return True
            
        except Exception:
            return True
    
    async def is_ip_blocked(self, ip: str) -> bool:
        """Verifica si una IP está bloqueada."""
        try:
            r = await self.get_redis()
            block_key = f"blocked_ip:{ip}"
            blocked = await r.exists(block_key)
            return bool(blocked)
        except Exception:
            return False
    
    async def dispatch(self, request: Request, call_next):
        # Obtener identificadores
        identifier, user_id = self.get_identifier(request)
        client_ip = self.get_client_ip(request)
        path = request.url.path
        
        # Verificar si IP está bloqueada
        if await self.is_ip_blocked(client_ip):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "IP temporalmente bloqueada por actividad sospechosa.",
                    "retry_after": 900
                },
                headers={"Retry-After": "900"}
            )
        
        # Determinar límites según el endpoint
        if self.is_login_endpoint(path):
            # Login: 3 intentos por minuto
            limit = self.login_requests_per_minute
            window = 60
            key_prefix = "ratelimit:login"
            
            # Verificar protección contra enumeration
            if not await self.check_enumeration_protection(client_ip, identifier):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Demasiados intentos de login. Intenta de nuevo en 15 minutos.",
                        "retry_after": 900
                    },
                    headers={
                        "Retry-After": "900",
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                    }
                )
                
        elif self.is_password_reset_endpoint(path):
            # Password reset: 1 intento por hora (muy restrictivo)
            limit = self.password_reset_per_hour
            window = 3600  # 1 hora
            key_prefix = "ratelimit:password_reset"
            
        elif self.is_candidates_post_endpoint(path, request.method):
            # POST /candidates: 10 por minuto
            limit = self.candidates_post_per_minute
            window = 60
            key_prefix = "ratelimit:candidates_post"
            
        elif self.is_auth_endpoint(path):
            limit = self.auth_requests_per_minute
            window = 60
            key_prefix = "ratelimit:auth"
            
        elif user_id:
            # Usuario autenticado - límite más alto
            limit = self.user_requests_per_minute
            window = 60
            key_prefix = "ratelimit:user"
            
        else:
            # Requests generales
            limit = self.requests_per_minute
            window = 60
            key_prefix = "ratelimit:ip"
        
        # Verificar rate limit
        allowed, current, ttl, remaining = await self.check_rate_limit(
            identifier, limit, window, key_prefix
        )
        
        if not allowed:
            # Loggear el evento
            from app.core.security_logging import SecurityLogger
            security_logger = SecurityLogger()
            await security_logger.log_rate_limit_hit(request, key_prefix, ttl)
            
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
        
        # Agregar headers de rate limit a la respuesta
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + ttl))
        
        return response


class RateLimitByUser:
    """Decorador para rate limiting específico por endpoint y usuario."""
    
    def __init__(
        self, 
        requests: int = 10, 
        window: int = 60,
        key_prefix: str = "custom"
    ):
        self.requests = requests
        self.window = window
        self.key_prefix = key_prefix
    
    async def __call__(self, request: Request) -> Optional[JSONResponse]:
        """Verifica el rate limit. Retorna None si está permitido, JSONResponse si excede."""
        from app.core.security_logging import SecurityLogger
        
        user_id = None
        auth_header = request.headers.get("Authorization", "")
        
        if auth_header.startswith("Bearer "):
            try:
                import jwt
                token = auth_header.split(" ")[1]
                payload = jwt.decode(
                    token, 
                    settings.SECRET_KEY, 
                    algorithms=[settings.ALGORITHM],
                    options={"verify_exp": False}
                )
                user_id = payload.get("sub")
            except Exception:
                pass
        
        if not user_id:
            # Si no hay usuario, usar IP
            forwarded = request.headers.get("X-Forwarded-For")
            user_id = forwarded.split(",")[0].strip() if forwarded else (
                request.client.host if request.client else "unknown"
            )
        
        key = f"{self.key_prefix}:{user_id}"
        
        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            current = await r.incr(key)
            
            if current == 1:
                await r.expire(key, self.window)
            
            ttl = await r.ttl(key)
            remaining = max(0, self.requests - current)
            
            if current > self.requests:
                security_logger = SecurityLogger()
                await security_logger.log_rate_limit_hit(request, self.key_prefix, ttl)
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Límite de {self.requests} solicitudes excedido.",
                        "retry_after": ttl
                    },
                    headers={
                        "Retry-After": str(ttl),
                        "X-RateLimit-Limit": str(self.requests),
                        "X-RateLimit-Remaining": "0",
                    }
                )
            
            await r.close()
            
        except Exception:
            # Fail open
            pass
        
        return None


class ProgressiveBlocker:
    """
    Bloqueo progresivo por IP basado en número de violaciones.
    Implementa backoff exponencial para IPs maliciosas.
    """
    
    # Ventanas de bloqueo en segundos (progresivo)
    BLOCK_DURATIONS = [300, 900, 3600, 86400]  # 5min, 15min, 1hr, 24hr
    
    def __init__(self):
        self.key_prefix = "progressive_block"
    
    async def get_redis(self) -> redis.Redis:
        return redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    async def record_violation(self, ip: str, reason: str = "rate_limit") -> int:
        """
        Registra una violación y retorna el nivel de bloqueo.
        
        Returns:
            Número de violaciones acumuladas
        """
        try:
            r = await self.get_redis()
            key = f"{self.key_prefix}:violations:{ip}"
            
            current = await r.incr(key)
            if current == 1:
                # Expirar después de 24 horas
                await r.expire(key, 86400)
            
            # Registrar timestamp de la violación
            timestamp_key = f"{self.key_prefix}:timestamps:{ip}"
            await r.zadd(timestamp_key, {str(datetime.utcnow().timestamp()): datetime.utcnow().timestamp()})
            await r.expire(timestamp_key, 86400)
            
            await r.close()
            return current
            
        except Exception:
            return 0
    
    async def get_block_duration(self, ip: str) -> int:
        """
        Calcula la duración de bloqueo basada en violaciones previas.
        
        Returns:
            Segundos de bloqueo
        """
        try:
            r = await self.get_redis()
            key = f"{self.key_prefix}:violations:{ip}"
            
            violations = int(await r.get(key) or 0)
            await r.close()
            
            # Determinar duración basada en nivel
            if violations == 0:
                return 0
            
            level = min(violations - 1, len(self.BLOCK_DURATIONS) - 1)
            return self.BLOCK_DURATIONS[level]
            
        except Exception:
            return 300  # Default 5 minutos
    
    async def is_blocked(self, ip: str) -> Tuple[bool, int]:
        """
        Verifica si una IP está bloqueada.
        
        Returns:
            Tuple de (está_bloqueada, segundos_restantes)
        """
        try:
            r = await self.get_redis()
            key = f"{self.key_prefix}:block:{ip}"
            
            ttl = await r.ttl(key)
            await r.close()
            
            if ttl > 0:
                return True, ttl
            return False, 0
            
        except Exception:
            return False, 0
    
    async def block_ip(self, ip: str, duration: Optional[int] = None) -> bool:
        """
        Bloquea una IP por la duración especificada o calculada.
        
        Args:
            ip: IP a bloquear
            duration: Duración en segundos (opcional)
        
        Returns:
            True si se bloqueó
        """
        try:
            if duration is None:
                duration = await self.get_block_duration(ip)
            
            r = await self.get_redis()
            key = f"{self.key_prefix}:block:{ip}"
            
            await r.setex(key, duration, "blocked")
            await r.close()
            
            return True
            
        except Exception:
            return False
    
    async def reset_violations(self, ip: str) -> bool:
        """Resetea el contador de violaciones de una IP."""
        try:
            r = await self.get_redis()
            
            await r.delete(f"{self.key_prefix}:violations:{ip}")
            await r.delete(f"{self.key_prefix}:timestamps:{ip}")
            await r.delete(f"{self.key_prefix}:block:{ip}")
            
            await r.close()
            return True
            
        except Exception:
            return False


# Singleton
progressive_blocker = ProgressiveBlocker()


async def check_progressive_block(ip: str) -> Tuple[bool, int]:
    """Verifica si una IP está bloqueada progresivamente."""
    return await progressive_blocker.is_blocked(ip)


async def apply_progressive_block(ip: str) -> int:
    """Aplica bloqueo progresivo y retorna duración."""
    await progressive_blocker.record_violation(ip)
    duration = await progressive_blocker.get_block_duration(ip)
    await progressive_blocker.block_ip(ip, duration)
    return duration
