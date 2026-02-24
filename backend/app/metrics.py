"""Métricas de Prometheus para ATS Platform."""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from functools import wraps
import time

# Registry global para métricas
REGISTRY = CollectorRegistry()

# ==========================================
# Métricas HTTP
# ==========================================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY
)

# ==========================================
# Métricas de Base de Datos
# ==========================================

db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections',
    registry=REGISTRY
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY
)

# ==========================================
# Métricas de Celery
# ==========================================

celery_tasks_total = Counter(
    'celery_task_total',
    'Total Celery tasks',
    ['task_name', 'state'],
    registry=REGISTRY
)

celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=REGISTRY
)

celery_worker_up = Gauge(
    'celery_worker_up',
    'Number of active Celery workers',
    registry=REGISTRY
)

celery_queue_length = Gauge(
    'celery_queue_length',
    'Current length of Celery queues',
    ['queue_name'],
    registry=REGISTRY
)

# ==========================================
# Métricas de Negocio
# ==========================================

candidates_total = Gauge(
    'ats_candidates_total',
    'Total number of candidates in the system',
    registry=REGISTRY
)

jobs_total = Gauge(
    'ats_jobs_total',
    'Total number of jobs in the system',
    ['status'],
    registry=REGISTRY
)

applications_total = Gauge(
    'ats_applications_total',
    'Total number of job applications',
    ['status'],
    registry=REGISTRY
)

# ==========================================
# Métricas de Seguridad
# ==========================================

security_events_total = Counter(
    'security_events_total',
    'Total security events',
    ['event_type', 'severity'],
    registry=REGISTRY
)

auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['result'],
    registry=REGISTRY
)

rate_limit_hits_total = Counter(
    'rate_limit_hits_total',
    'Total rate limit hits',
    ['endpoint'],
    registry=REGISTRY
)

# ==========================================
# Funciones de utilidad
# ==========================================

def get_prometheus_metrics():
    """Generate Prometheus metrics output."""
    return generate_latest(REGISTRY)


def track_security_event(event_type: str, severity: str = "info", labels: dict = None):
    """Track a security event."""
    security_events_total.labels(
        event_type=event_type,
        severity=severity
    ).inc()


def track_auth_attempt(result: str):
    """Track an authentication attempt."""
    auth_attempts_total.labels(result=result).inc()


def track_rate_limit_hit(endpoint: str):
    """Track a rate limit hit."""
    rate_limit_hits_total.labels(endpoint=endpoint).inc()


def init_metrics(app_name: str = "ats-platform", app_version: str = "1.0.0"):
    """Initialize metrics with app info."""
    from prometheus_client import Info
    
    app_info = Info('app_info', 'Application information', registry=REGISTRY)
    app_info.info({
        'name': app_name,
        'version': app_version
    })


def timed(metric: Histogram):
    """Decorator to time function execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.observe(duration)
        return wrapper
    return decorator
