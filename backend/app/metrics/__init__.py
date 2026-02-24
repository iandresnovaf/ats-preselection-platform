# Observability Module - Métricas de negocio y auditoría
"""
Módulo de observabilidad para el ATS Platform.
Incluye métricas de negocio, auditoría y trazas distribuidas.
"""
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
from functools import wraps
import time
from typing import Callable, Any

# Métricas de sistema - usadas por health checks
db_connections_active = Gauge(
    'ats_db_connections_active',
    'Conexiones activas a la base de datos'
)

db_connections_idle = Gauge(
    'ats_db_connections_idle',
    'Conexiones inactivas a la base de datos'
)

disk_usage_percent = Gauge(
    'ats_disk_usage_percent',
    'Porcentaje de uso de disco',
    ['path']
)

process_memory_usage_percent = Gauge(
    'ats_process_memory_usage_percent',
    'Porcentaje de uso de memoria del proceso'
)

# =============================================================================
# Métricas de Negocio - ATS Core
# =============================================================================

# Contador de aplicaciones creadas
applications_created_total = Counter(
    'ats_applications_created_total',
    'Total de aplicaciones creadas',
    ['role_id', 'source']
)

# Contador de aplicaciones por etapa
applications_by_stage = Counter(
    'ats_applications_by_stage',
    'Aplicaciones por etapa del pipeline',
    ['stage', 'role_id']
)

# Gauge de aplicaciones actuales por etapa
applications_current_by_stage = Gauge(
    'ats_applications_current_by_stage',
    'Aplicaciones actuales por etapa',
    ['stage', 'role_id']
)

# Tasa de éxito de extracción de CVs
cv_extraction_total = Counter(
    'ats_cv_extraction_total',
    'Total de extracciones de CV',
    ['method', 'status']  # status: success, failed, partial
)

cv_extraction_success_rate = Gauge(
    'ats_cv_extraction_success_rate',
    'Tasa de éxito de extracción de CVs',
    ['method']
)

# Histograma de tiempo de contratación (en días)
time_to_hire_days = Histogram(
    'ats_time_to_hire_days',
    'Días desde aplicación hasta contratación',
    buckets=[1, 3, 7, 14, 21, 30, 45, 60, 90, 120]
)

# Tasa de conversión de candidatos
candidate_conversion_total = Counter(
    'ats_candidate_conversion_total',
    'Total de conversiones de candidatos',
    ['from_stage', 'to_stage']
)

candidate_conversion_rate = Gauge(
    'ats_candidate_conversion_rate',
    'Tasa de conversión entre etapas',
    ['stage']
)

# Métricas de roles activos
active_roles = Gauge(
    'ats_active_roles',
    'Número de roles/vacantes activos',
    ['client_id']
)

# Métricas de candidatos por fuente
candidates_by_source = Counter(
    'ats_candidates_by_source_total',
    'Candidatos por fuente de ingreso',
    ['source']
)

# =============================================================================
# Métricas de Seguridad
# =============================================================================

# Login attempts
login_attempts_total = Counter(
    'ats_security_login_attempts_total',
    'Intentos de login',
    ['status']  # success, failed
)

# Rate limiting hits
rate_limit_hits_total = Counter(
    'ats_security_rate_limit_hits_total',
    'Rate limit alcanzados',
    ['endpoint', 'limit_type']
)

# Accesos no autorizados
unauthorized_access_total = Counter(
    'ats_security_unauthorized_access_total',
    'Accesos no autorizados detectados',
    ['reason', 'endpoint']
)

# Errores HTTP
http_errors_total = Counter(
    'ats_http_errors_total',
    'Errores HTTP 4xx/5xx',
    ['status_code', 'endpoint', 'method']
)

# Cambios de permisos
permission_changes_total = Counter(
    'ats_security_permission_changes_total',
    'Cambios de permisos/roles',
    ['action', 'target_user_id']
)

# Acceso a datos PII
pii_access_total = Counter(
    'ats_security_pii_access_total',
    'Accesos a datos sensibles (PII)',
    ['resource_type', 'action', 'user_id']
)

# Exportación de datos
export_operations_total = Counter(
    'ats_export_operations_total',
    'Operaciones de exportación de datos',
    ['resource_type', 'format', 'user_id']
)

# =============================================================================
# Métricas de Rendimiento
# =============================================================================

# Latencia de endpoints
http_request_duration_seconds = Histogram(
    'ats_http_request_duration_seconds',
    'Duración de requests HTTP',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Métricas de LLM/AI
llm_requests_total = Counter(
    'ats_llm_requests_total',
    'Requests a LLM/OpenAI',
    ['model', 'status', 'operation']
)

llm_request_duration_seconds = Histogram(
    'ats_llm_request_duration_seconds',
    'Duración de requests a LLM',
    ['model', 'operation'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

llm_tokens_used_total = Counter(
    'ats_llm_tokens_used_total',
    'Tokens utilizados en LLM',
    ['model', 'token_type']  # prompt, completion
)

# Métricas de Celery
celery_tasks_total = Counter(
    'ats_celery_tasks_total',
    'Tareas de Celery ejecutadas',
    ['task_name', 'status']  # success, failure, retry
)

celery_task_duration_seconds = Histogram(
    'ats_celery_task_duration_seconds',
    'Duración de tareas Celery',
    ['task_name'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# Métricas de base de datos
db_query_duration_seconds = Histogram(
    'ats_db_query_duration_seconds',
    'Duración de queries a BD',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# =============================================================================
# Métricas de Trazas (OpenTelemetry)
# =============================================================================

# Información de la aplicación
app_info = Info(
    'ats_app_info',
    'Información de la aplicación ATS'
)

# Trace context
trace_spans_total = Counter(
    'ats_trace_spans_total',
    'Total de spans creados',
    ['operation', 'status']
)

# =============================================================================
# Funciones de utilidad
# =============================================================================

def get_prometheus_metrics() -> bytes:
    """Genera métricas en formato Prometheus."""
    return generate_latest(REGISTRY)

def set_app_info(version: str, environment: str):
    """Setea información de la aplicación."""
    app_info.info({
        'version': version,
        'environment': environment
    })

def track_business_metric(metric_name: str, value: float = 1.0, labels: dict = None):
    """Registra una métrica de negocio.
    
    Args:
        metric_name: Nombre de la métrica
        value: Valor a registrar (default 1.0)
        labels: Labels opcionales
    """
    labels = labels or {}
    
    if metric_name == 'application_created':
        applications_created_total.labels(**labels).inc(value)
    elif metric_name == 'stage_change':
        applications_by_stage.labels(**labels).inc(value)
    elif metric_name == 'cv_extraction':
        cv_extraction_total.labels(**labels).inc(value)
        # Actualizar tasa de éxito
        if labels.get('status') == 'success':
            method = labels.get('method', 'unknown')
            # Esto es simplificado, en producción necesitaría tracking de total
            cv_extraction_success_rate.labels(method=method).set(1.0)
    elif metric_name == 'time_to_hire':
        time_to_hire_days.observe(value)
    elif metric_name == 'conversion':
        candidate_conversion_total.labels(**labels).inc(value)

def track_security_event(event_type: str, labels: dict = None):
    """Registra un evento de seguridad.
    
    Args:
        event_type: Tipo de evento (login_failed, unauthorized_access, etc.)
        labels: Labels adicionales
    """
    labels = labels or {}
    
    if event_type == 'login_attempt':
        login_attempts_total.labels(**labels).inc()
    elif event_type == 'rate_limit_hit':
        rate_limit_hits_total.labels(**labels).inc()
    elif event_type == 'unauthorized_access':
        unauthorized_access_total.labels(**labels).inc()
    elif event_type == 'permission_change':
        permission_changes_total.labels(**labels).inc()
    elif event_type == 'pii_access':
        pii_access_total.labels(**labels).inc()
    elif event_type == 'export':
        export_operations_total.labels(**labels).inc()
    elif event_type == 'http_error':
        http_errors_total.labels(**labels).inc()

def track_llm_request(model: str, operation: str, duration: float, tokens_prompt: int = 0, tokens_completion: int = 0, success: bool = True):
    """Registra una llamada a LLM.
    
    Args:
        model: Modelo utilizado (gpt-4, gpt-3.5-turbo, etc.)
        operation: Operación realizada (cv_extraction, matching, etc.)
        duration: Duración en segundos
        tokens_prompt: Tokens de prompt
        tokens_completion: Tokens de completado
        success: Si fue exitoso
    """
    status = 'success' if success else 'failed'
    llm_requests_total.labels(model=model, operation=operation, status=status).inc()
    llm_request_duration_seconds.labels(model=model, operation=operation).observe(duration)
    
    if tokens_prompt > 0:
        llm_tokens_used_total.labels(model=model, token_type='prompt').inc(tokens_prompt)
    if tokens_completion > 0:
        llm_tokens_used_total.labels(model=model, token_type='completion').inc(tokens_completion)

def track_celery_task(task_name: str, status: str, duration: float):
    """Registra una tarea de Celery.
    
    Args:
        task_name: Nombre de la tarea
        status: Estado (success, failure, retry)
        duration: Duración en segundos
    """
    celery_tasks_total.labels(task_name=task_name, status=status).inc()
    celery_task_duration_seconds.labels(task_name=task_name).observe(duration)

def track_db_query(operation: str, table: str, duration: float):
    """Registra una query a base de datos.
    
    Args:
        operation: Tipo de operación (SELECT, INSERT, etc.)
        table: Tabla afectada
        duration: Duración en segundos
    """
    db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)

# Decorador para medir tiempo de ejecución
def timed(metric_name: str, labels: dict = None):
    """Decorador para medir tiempo de ejecución de funciones.
    
    Args:
        metric_name: Nombre de la métrica
        labels: Labels para la métrica
    """
    labels = labels or {}
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                # Registrar métrica según tipo
                if metric_name.startswith('llm_'):
                    track_llm_request(
                        model=labels.get('model', 'unknown'),
                        operation=labels.get('operation', func.__name__),
                        duration=duration,
                        success=True
                    )
                elif metric_name.startswith('db_'):
                    track_db_query(
                        operation=labels.get('operation', 'SELECT'),
                        table=labels.get('table', 'unknown'),
                        duration=duration
                    )
                return result
            except Exception:
                duration = time.time() - start_time
                if metric_name.startswith('llm_'):
                    track_llm_request(
                        model=labels.get('model', 'unknown'),
                        operation=labels.get('operation', func.__name__),
                        duration=duration,
                        success=False
                    )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                if metric_name.startswith('celery_'):
                    track_celery_task(
                        task_name=labels.get('task_name', func.__name__),
                        status='success',
                        duration=duration
                    )
                return result
            except Exception:
                duration = time.time() - start_time
                if metric_name.startswith('celery_'):
                    track_celery_task(
                        task_name=labels.get('task_name', func.__name__),
                        status='failure',
                        duration=duration
                    )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Import para el decorator
import asyncio

# =============================================================================
# Inicialización
# =============================================================================

def init_metrics(app_version: str = "1.0.0", environment: str = "development"):
    """Inicializa las métricas con información de la app."""
    set_app_info(app_version, environment)
