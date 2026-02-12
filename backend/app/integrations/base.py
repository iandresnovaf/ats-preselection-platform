"""Base connector class for external integrations.

Provides common functionality for all integrations:
- Circuit breaker pattern
- Retry with exponential backoff
- Rate limiting
- Request/response logging
- Token management
"""
import asyncio
import hashlib
import hmac
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union
from functools import wraps

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.security import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Estados del circuit breaker."""
    CLOSED = "closed"      # Funcionamiento normal
    OPEN = "open"          # Circuito abierto, rechazando requests
    HALF_OPEN = "half_open"  # Probando si el servicio recuperó


@dataclass
class CircuitBreakerConfig:
    """Configuración del circuit breaker."""
    failure_threshold: int = 5          # Fallos antes de abrir
    recovery_timeout: int = 60          # Segundos antes de intentar recuperación
    half_open_max_calls: int = 3        # Llamadas en estado half-open
    success_threshold: int = 2          # Éxitos para cerrar circuito


@dataclass
class RateLimitConfig:
    """Configuración de rate limiting."""
    requests_per_second: float = 1.0
    burst_size: int = 5
    max_retries: int = 3
    base_delay: float = 1.0             # Segundos base para backoff
    max_delay: float = 60.0             # Máximo delay entre retries


@dataclass
class SyncResult:
    """Resultado de una sincronización."""
    success: bool
    items_processed: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    next_page_token: Optional[str] = None
    
    def merge(self, other: 'SyncResult') -> 'SyncResult':
        """Combinar con otro resultado."""
        return SyncResult(
            success=self.success and other.success,
            items_processed=self.items_processed + other.items_processed,
            items_created=self.items_created + other.items_created,
            items_updated=self.items_updated + other.items_updated,
            items_failed=self.items_failed + other.items_failed,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            metadata={**self.metadata, **other.metadata},
            duration_ms=self.duration_ms + other.duration_ms,
            next_page_token=other.next_page_token
        )


class CircuitBreaker:
    """Circuit breaker para proteger contra fallos en cascada."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Ejecutar función con protección del circuit breaker."""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.success_count = 0
                    logger.info(f"Circuit {self.name}: Transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")
            
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpen(f"Circuit {self.name} is HALF_OPEN (max calls reached)")
                self.half_open_calls += 1
        
        # Ejecutar la función fuera del lock
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self):
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info(f"Circuit {self.name}: Transitioning to CLOSED")
            else:
                self.failure_count = 0
    
    async def _on_failure(self):
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name}: Transitioning to OPEN (half-open failure)")
            elif self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name}: Transitioning to OPEN ({self.failure_count} failures)")
    
    def _should_attempt_reset(self) -> bool:
        if not self.last_failure_time:
            return True
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout
    
    def get_state(self) -> Dict[str, Any]:
        """Obtener estado actual del circuit breaker."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class CircuitBreakerOpen(Exception):
    """Excepción cuando el circuit breaker está abierto."""
    pass


class RateLimiter:
    """Rate limiter con token bucket algorithm."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.burst_size
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Adquirir un token, esperando si es necesario."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(
                self.config.burst_size,
                self.tokens + elapsed * self.config.requests_per_second
            )
            self.last_update = now
            
            if self.tokens < 1:
                # Calcular tiempo de espera
                wait_time = (1 - self.tokens) / self.config.requests_per_second
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


def with_retry(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """Decorador para reintentar con exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except CircuitBreakerOpen:
                    raise  # No reintentar si el circuit breaker está abierto
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        # Exponential backoff con jitter
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = delay * 0.1 * (asyncio.get_event_loop().time() % 1)
                        await asyncio.sleep(delay + jitter)
                        logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}")
            
            raise last_exception
        return wrapper
    return decorator


T = TypeVar('T')


class BaseConnector(ABC, Generic[T]):
    """Base class para conectores de integración.
    
    Type parameter T representa el tipo de configuración específica.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        config: T,
        rate_limit_config: Optional[RateLimitConfig] = None,
        circuit_config: Optional[CircuitBreakerConfig] = None
    ):
        self.db = db
        self.config = config
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        self.circuit_breaker = CircuitBreaker(
            name=self.__class__.__name__,
            config=circuit_config or CircuitBreakerConfig()
        )
        self.http_client: Optional[httpx.AsyncClient] = None
        self._cache_prefix = f"connector:{self.__class__.__name__.lower()}"
    
    async def __aenter__(self):
        """Context manager entry."""
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Autenticar con el servicio externo.
        
        Returns:
            True si la autenticación fue exitosa.
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """Probar la conexión con el servicio.
        
        Returns:
            (success, message)
        """
        pass
    
    @abstractmethod
    async def sync_jobs(self, **kwargs) -> SyncResult:
        """Sincronizar puestos de trabajo.
        
        Returns:
            Resultado de la sincronización.
        """
        pass
    
    @abstractmethod
    async def sync_candidates(self, **kwargs) -> SyncResult:
        """Sincronizar candidatos.
        
        Returns:
            Resultado de la sincronización.
        """
        pass
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retry_count: int = 0
    ) -> httpx.Response:
        """Hacer request HTTP con rate limiting y retry.
        
        Args:
            method: HTTP method
            url: URL del endpoint
            headers: Headers HTTP
            json_data: Body JSON
            params: Query params
            retry_count: Contador de reintentos (uso interno)
            
        Returns:
            Respuesta HTTP
            
        Raises:
            CircuitBreakerOpen: Si el circuit breaker está abierto
            httpx.HTTPError: Si hay error en la request
        """
        # Rate limiting
        await self.rate_limiter.acquire()
        
        # Circuit breaker
        async def do_request():
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized. Use async context manager.")
            
            response = await self.http_client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params
            )
            response.raise_for_status()
            return response
        
        try:
            return await self.circuit_breaker.call(do_request)
        except CircuitBreakerOpen:
            raise
        except httpx.HTTPStatusError as e:
            # Retry en errores 5xx y 429 (rate limit)
            if e.response.status_code in (429, 500, 502, 503, 504):
                if retry_count < self.rate_limiter.config.max_retries:
                    delay = min(
                        self.rate_limiter.config.base_delay * (2 ** retry_count),
                        self.rate_limiter.config.max_delay
                    )
                    logger.warning(f"Request failed with {e.response.status_code}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    return await self._make_request(
                        method, url, headers, json_data, params, retry_count + 1
                    )
            raise
    
    async def _get_cached(self, key: str, ttl: int = 300) -> Optional[Any]:
        """Obtener valor del cache."""
        return await cache.get(f"{self._cache_prefix}:{key}")
    
    async def _set_cached(self, key: str, value: Any, ttl: int = 300):
        """Guardar valor en cache."""
        await cache.set(f"{self._cache_prefix}:{key}", value, ttl=ttl)
    
    async def _invalidate_cache(self, key: str):
        """Invalidar cache key."""
        await cache.delete(f"{self._cache_prefix}:{key}")
    
    def _encrypt_token(self, token: str) -> str:
        """Encriptar token para almacenamiento."""
        return encrypt_value(token)
    
    def _decrypt_token(self, encrypted_token: str) -> str:
        """Desencriptar token."""
        return decrypt_value(encrypted_token)
    
    def _generate_webhook_signature(self, payload: bytes, secret: str) -> str:
        """Generar firma HMAC para webhooks."""
        return hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
    
    def _verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verificar firma HMAC de webhook."""
        expected = self._generate_webhook_signature(payload, secret)
        return hmac.compare_digest(expected, signature)
    
    def _safe_log(self, data: Dict, sensitive_keys: List[str] = None) -> Dict:
        """Crear versión segura de datos para logging.
        
        Args:
            data: Datos a loguear
            sensitive_keys: Claves sensibles a enmascarar
            
        Returns:
            Copia de datos con valores sensibles enmascarados
        """
        if sensitive_keys is None:
            sensitive_keys = ['token', 'password', 'secret', 'key', 'auth']
        
        result = {}
        for k, v in data.items():
            if any(sk in k.lower() for sk in sensitive_keys):
                result[k] = '*' * min(len(str(v)), 8) if v else None
            elif isinstance(v, dict):
                result[k] = self._safe_log(v, sensitive_keys)
            else:
                result[k] = v
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del conector."""
        return {
            "connector": self.__class__.__name__,
            "circuit_breaker": self.circuit_breaker.get_state(),
            "rate_limiter": {
                "tokens_available": self.rate_limiter.tokens,
                "config": {
                    "requests_per_second": self.rate_limiter.config.requests_per_second,
                    "burst_size": self.rate_limiter.config.burst_size
                }
            }
        }


class WebhookHandler(ABC):
    """Base class para handlers de webhooks."""
    
    def __init__(self, connector: BaseConnector):
        self.connector = connector
    
    @abstractmethod
    async def handle(self, payload: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """Procesar webhook recibido.
        
        Args:
            payload: Body del webhook
            headers: Headers HTTP
            
        Returns:
            Resultado del procesamiento
        """
        pass
    
    @abstractmethod
    def verify_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verificar firma del webhook."""
        pass
