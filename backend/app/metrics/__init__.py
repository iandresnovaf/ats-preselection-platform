"""Sistema de métricas con Prometheus para FastAPI."""
import time
import psutil
import os
from typing import Optional, Callable
from functools import wraps

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from fastapi.routing import APIRoute


# ============================================
# Métricas de HTTP/Endpoints
# ============================================

# Contador de requests HTTP
http_requests_total = Counter(
    'http_requests_total',
    'Total de requests HTTP',
    ['method', 'endpoint', 'status_code']
)

# Histograma de latencia de requests
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'Duración de requests HTTP en segundos',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Contador de errores HTTP
http_errors_total = Counter(
    'http_errors_total',
    'Total de errores HTTP por código',
    ['method', 'endpoint', 'error_type']  # error_type: 4xx, 5xx
)

# ============================================
# Métricas de Sistema (CPU/Memoria)
# ============================================

# Uso de CPU
process_cpu_usage = Gauge(
    'process_cpu_usage_percent',
    'Uso de CPU del proceso en porcentaje'
)

# Uso de memoria
process_memory_usage_bytes = Gauge(
    'process_memory_usage_bytes',
    'Uso de memoria del proceso en bytes'
)

process_memory_usage_percent = Gauge(
    'process_memory_usage_percent',
    'Uso de memoria del proceso en porcentaje'
)

# Uso de disco
disk_usage_bytes = Gauge(
    'disk_usage_bytes',
    'Uso de disco en bytes',
    ['path']
)

disk_usage_percent = Gauge(
    'disk_usage_percent',
    'Uso de disco en porcentaje',
    ['path']
)

# ============================================
# Métricas de Base de Datos
# ============================================

db_connections_active = Gauge(
    'db_connections_active',
    'Número de conexiones a BD activas'
)

db_connections_idle = Gauge(
    'db_connections_idle',
    'Número de conexiones a BD inactivas'
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Duración de queries de BD en segundos',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# ============================================
# Métricas de Cache (Redis)
# ============================================

cache_hits_total = Counter(
    'cache_hits_total',
    'Total de cache hits',
    ['cache_name']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total de cache misses',
    ['cache_name']
)

cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Ratio de cache hits (0-1)',
    ['cache_name']
)

# ============================================
# Métricas de LLM/APIs Externas
# ============================================

llm_requests_total = Counter(
    'llm_requests_total',
    'Total de requests a LLM API',
    ['provider', 'model', 'status']  # status: success, error
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'Duración de requests a LLM en segundos',
    ['provider', 'model'],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 15.0, 30.0, 60.0]
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total de tokens usados',
    ['provider', 'model', 'token_type']  # token_type: prompt, completion, total
)

llm_cost_dollars = Counter(
    'llm_cost_dollars_total',
    'Costo acumulado de LLM API en dólares',
    ['provider', 'model']
)

# ============================================
# Métricas de Negocio
# ============================================

# Info de la aplicación
app_info = Info(
    'app_info',
    'Información de la aplicación'
)

# Workers activos
active_workers = Gauge(
    'active_workers',
    'Número de workers activos'
)

# Jobs en cola
jobs_in_queue = Gauge(
    'jobs_in_queue',
    'Número de jobs en cola',
    ['queue_name']
)

# ============================================
# Funciones de ayuda
# ============================================

class MetricsRoute(APIRoute):
    """Ruta personalizada que registra métricas automáticamente."""
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            # Capturar información del request
            method = request.method
            path = request.url.path
            
            # Iniciar timer
            start_time = time.time()
            
            try:
                response = await original_route_handler(request)
                status_code = str(response.status_code)
                
                # Registrar métricas
                http_requests_total.labels(
                    method=method,
                    endpoint=path,
                    status_code=status_code
                ).inc()
                
                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=path
                ).observe(time.time() - start_time)
                
                # Registrar errores
                if response.status_code >= 400:
                    error_type = '4xx' if response.status_code < 500 else '5xx'
                    http_errors_total.labels(
                        method=method,
                        endpoint=path,
                        error_type=error_type
                    ).inc()
                
                return response
                
            except Exception as exc:
                # Registrar error en caso de excepción
                http_errors_total.labels(
                    method=method,
                    endpoint=path,
                    error_type='5xx'
                ).inc()
                raise
        
        return custom_route_handler


def track_cache_hit(cache_name: str = "default"):
    """Registra un cache hit."""
    cache_hits_total.labels(cache_name=cache_name).inc()
    _update_cache_ratio(cache_name)


def track_cache_miss(cache_name: str = "default"):
    """Registra un cache miss."""
    cache_misses_total.labels(cache_name=cache_name).inc()
    _update_cache_ratio(cache_name)


def _update_cache_ratio(cache_name: str):
    """Actualiza el ratio de cache hits."""
    hits = cache_hits_total.labels(cache_name=cache_name)._value.get()
    misses = cache_misses_total.labels(cache_name=cache_name)._value.get()
    total = hits + misses
    if total > 0:
        ratio = hits / total
        cache_hit_ratio.labels(cache_name=cache_name).set(ratio)


def track_llm_request(provider: str, model: str, duration: float, 
                      tokens_prompt: int = 0, tokens_completion: int = 0,
                      success: bool = True, cost: float = 0.0):
    """Registra métricas de un request a LLM.
    
    Args:
        provider: Proveedor del LLM (openai, anthropic, etc.)
        model: Modelo usado (gpt-4, claude-3, etc.)
        duration: Duración en segundos
        tokens_prompt: Tokens de prompt
        tokens_completion: Tokens de completion
        success: Si el request fue exitoso
        cost: Costo estimado en dólares
    """
    status = 'success' if success else 'error'
    
    llm_requests_total.labels(
        provider=provider,
        model=model,
        status=status
    ).inc()
    
    llm_request_duration_seconds.labels(
        provider=provider,
        model=model
    ).observe(duration)
    
    if tokens_prompt > 0:
        llm_tokens_total.labels(
            provider=provider,
            model=model,
            token_type='prompt'
        ).inc(tokens_prompt)
    
    if tokens_completion > 0:
        llm_tokens_total.labels(
            provider=provider,
            model=model,
            token_type='completion'
        ).inc(tokens_completion)
    
    total_tokens = tokens_prompt + tokens_completion
    if total_tokens > 0:
        llm_tokens_total.labels(
            provider=provider,
            model=model,
            token_type='total'
        ).inc(total_tokens)
    
    if cost > 0:
        llm_cost_dollars.labels(
            provider=provider,
            model=model
        ).inc(cost)


def track_db_query(operation: str, duration: float):
    """Registra la duración de una query de BD."""
    db_query_duration_seconds.labels(operation=operation).observe(duration)


def update_system_metrics():
    """Actualiza métricas de sistema (CPU, memoria, disco)."""
    # CPU
    cpu_percent = psutil.Process().cpu_percent(interval=0.1)
    process_cpu_usage.set(cpu_percent)
    
    # Memoria
    memory_info = psutil.Process().memory_info()
    process_memory_usage_bytes.set(memory_info.rss)
    
    memory_percent = psutil.Process().memory_percent()
    process_memory_usage_percent.set(memory_percent)
    
    # Disco
    disk = psutil.disk_usage('/')
    disk_usage_bytes.labels(path='/').set(disk.used)
    disk_usage_percent.labels(path='/').set(disk.percent)


def set_app_info(version: str, environment: str):
    """Setea la información de la aplicación."""
    app_info.info({
        'version': version,
        'environment': environment,
        'python_version': os.sys.version
    })


def get_prometheus_metrics():
    """Genera el output de métricas para Prometheus."""
    update_system_metrics()
    return generate_latest()


# Decorator para funciones
def timed(metric_name: str, labels: Optional[dict] = None):
    """Decorator para medir tiempo de ejecución de funciones."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                # Aquí podrías enviar a un histograma personalizado
        return wrapper
    return decorator
