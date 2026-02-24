"""Aplicación FastAPI principal."""
import re
import time
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine, Base
from app.core.rate_limit import RateLimitMiddleware
from app.core.csrf import CSRFMiddleware
from app.core.security_logging import SecurityLogger
from app.api import config, auth, users, jobs, candidates, evaluations, matching, health, rhtools, audit, metrics as metrics_api
# Core ATS API - Nuevo sistema de headhunting
from app.api.v1 import api_router as core_ats_router
from app.api.document_pipeline import router as pipeline_router
from app.api.auth import limiter as auth_limiter

# Logger
logger = logging.getLogger(__name__)

# Logger de seguridad
security_logger = SecurityLogger()

# Rate Limiter global
limiter = Limiter(key_func=get_remote_address)


def is_uuid_validation_error(errors: list) -> bool:
    """
    Verifica si el error de validación es específicamente por UUID inválido.
    
    Args:
        errors: Lista de errores de validación de Pydantic
        
    Returns:
        bool: True si es un error de UUID
    """
    for error in errors:
        # Verificar si es error de tipo UUID
        if error.get('type') == 'uuid_parsing':
            return True
        if error.get('type') == 'type_error.uuid':
            return True
        # Verificar en el mensaje
        msg = str(error.get('msg', '')).lower()
        if 'uuid' in msg or 'uuid_parsing' in msg:
            return True
        # Verificar en ctx si existe
        ctx = error.get('ctx', {})
        if isinstance(ctx, dict) and 'error' in str(ctx).lower():
            if 'uuid' in str(ctx).lower():
                return True
    return False


def extract_uuid_param_name(errors: list) -> str:
    """Extrae el nombre del parámetro UUID que falló la validación."""
    for error in errors:
        loc = error.get('loc', [])
        if len(loc) >= 2 and loc[0] == 'path':
            return str(loc[1])
    return "id"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo del ciclo de vida de la aplicación."""
    # Startup
    print("🚀 Starting ATS Platform...")
    logger.info("Iniciando ATS Platform...")
    
    # =============================================================================
    # Inicializar OpenTelemetry Tracing
    # =============================================================================
    jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")
    otel_enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"
    
    if otel_enabled:
        from app.core.tracing import init_tracer
        tracer = init_tracer(
            jaeger_endpoint=jaeger_endpoint,
            console_export=settings.DEBUG,
            sample_rate=float(os.getenv("TRACING_SAMPLE_RATE", "1.0"))
        )
        if tracer:
            print(f"✅ OpenTelemetry tracing initialized (Jaeger: {jaeger_endpoint})")
            logger.info(f"OpenTelemetry tracing inicializado (Jaeger: {jaeger_endpoint})")
        else:
            print("⚠️ OpenTelemetry tracing no disponible (verifique instalación)")
            logger.warning("OpenTelemetry tracing no disponible")
    else:
        print("ℹ️ OpenTelemetry tracing deshabilitado (OTEL_ENABLED=false)")
        logger.info("OpenTelemetry tracing deshabilitado")
    
    # =============================================================================
    # Inicializar Loki Logging
    # =============================================================================
    loki_url = os.getenv("LOKI_URL", "http://loki:3100")
    loki_enabled = os.getenv("LOKI_ENABLED", "false").lower() == "true"
    
    if loki_enabled:
        from app.core.loki_logging import setup_loki_logging
        loki_handler = setup_loki_logging(
            loki_url=loki_url,
            service_name="ats-platform",
            environment=settings.ENVIRONMENT,
            level=logging.INFO if not settings.DEBUG else logging.DEBUG,
            enable_console=settings.DEBUG
        )
        if loki_handler:
            print(f"✅ Loki logging initialized ({loki_url})")
            logger.info(f"Loki logging inicializado ({loki_url})")
        else:
            print("⚠️ Loki logging no disponible, usando consola")
            logger.warning("Loki logging no disponible, usando consola")
    else:
        print("ℹ️ Loki logging deshabilitado (LOKI_ENABLED=false), usando consola")
        logger.info("Loki logging deshabilitado, usando consola")
    
    # =============================================================================
    # Inicializar Métricas Prometheus
    # =============================================================================
    from app.metrics import init_metrics
    init_metrics(
        app_version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT
    )
    print("✅ Prometheus metrics initialized")
    logger.info("Métricas Prometheus inicializadas")
    
    # Crear tablas (en desarrollo)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database tables created")
    logger.info("Tablas de base de datos creadas")
    
    # Verificar encriptación PII
    from app.core.security import encryption_manager
    if encryption_manager._fernet:
        print("✅ PII encryption ready")
        logger.info("Encriptación PII lista")
    else:
        logger.warning("Encriptación PII no inicializada - revisar ENCRYPTION_KEY")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    logger.info("Deteniendo ATS Platform...")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Plataforma de preselección automatizada de candidatos",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
)

# Configurar rate limiter en la app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Trusted Hosts Middleware - protege contra Host header attacks
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# =============================================================================
# OpenTelemetry Tracing Middleware
# =============================================================================
if os.getenv("OTEL_ENABLED", "false").lower() == "true":
    from app.core.tracing import create_tracing_middleware
    
    @app.middleware("http")
    async def tracing_middleware(request: Request, call_next):
        """Middleware para trazas distribuidas con OpenTelemetry."""
        middleware = create_tracing_middleware("ats-platform")
        return await middleware(request, call_next)
else:
    # Middleware simple para agregar X-Trace-ID sin OpenTelemetry
    @app.middleware("http")
    async def tracing_middleware(request: Request, call_next):
        """Middleware simple para generar X-Trace-ID."""
        import uuid
        response = await call_next(request)
        if not response.headers.get("X-Trace-ID"):
            response.headers["X-Trace-ID"] = str(uuid.uuid4())
        return response

# =============================================================================
# Prometheus Metrics Middleware
# =============================================================================
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware para recolectar métricas de requests."""
    from app.metrics import http_request_duration_seconds, track_security_event
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Registrar métrica de duración
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).observe(duration)
        
        # Registrar errores 4xx/5xx
        if response.status_code >= 400:
            track_security_event(
                'http_error',
                labels={
                    'status_code': str(response.status_code),
                    'endpoint': request.url.path,
                    'method': request.method
                }
            )
        
        return response
        
    except Exception as exc:
        duration = time.time() - start_time
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=500
        ).observe(duration)
        
        track_security_event(
            'http_error',
            labels={
                'status_code': '500',
                'endpoint': request.url.path,
                'method': request.method
            }
        )
        raise

# Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Middleware para agregar headers de seguridad HTTP."""
    response = await call_next(request)
    
    # Content Security Policy - Mejorado para reducir superficie de ataque XSS
    if settings.DEBUG:
        # CSP relajado para desarrollo/documentación API
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
    else:
        # CSP estricto para producción
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests;"
        )
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # XSS Protection (legacy but still useful)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # HSTS (solo en producción con HTTPS)
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions Policy (formerly Feature-Policy)
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), "
        "camera=(), "
        "geolocation=(), "
        "gyroscope=(), "
        "magnetometer=(), "
        "microphone=(), "
        "payment=(), "
        "usb=()"
    )
    
    # Cache control para APIs
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    
    # Agregar Trace-ID header (de OpenTelemetry o generar uno)
    trace_id = request.headers.get("X-Trace-ID")
    if not trace_id:
        from app.core.tracing import get_trace_id
        trace_id = get_trace_id()
        if trace_id:
            response.headers["X-Trace-ID"] = trace_id
    
    return response

# CSRF Protection Middleware
@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    """Middleware para protección CSRF."""
    from app.metrics import track_security_event
    
    # Solo verificar métodos mutables
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # Skip para endpoints de autenticación (usamos tokens JWT)
        path = request.url.path
        exempt_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/logout",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/change-password",
            "/api/v1/auth/change-email",
        ]
        
        if not any(path.startswith(ep) for ep in exempt_paths):
            # Verificar Content-Type para APIs
            content_type = request.headers.get("content-type", "")
            
            # Para APIs JSON, verificar que sea application/json
            if request.method in ("POST", "PUT", "PATCH"):
                if not (content_type.startswith("application/json") or 
                        content_type.startswith("multipart/form-data")):
                    await security_logger.log_unauthorized_access(
                        request,
                        f"CSRF: Content-Type inválido: {content_type}"
                    )
                    track_security_event(
                        'unauthorized_access',
                        labels={
                            'reason': 'invalid_content_type',
                            'endpoint': path
                        }
                    )
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Content-Type no válido"}
                    )
            
            # Verificar Origin/Referer para SameSite protection
            origin = request.headers.get("origin", "")
            allowed_origins = settings.get_cors_origins()
            
            # Si hay Origin header, debe coincidir con allowed origins
            if origin and origin not in allowed_origins:
                await security_logger.log_unauthorized_access(
                    request,
                    f"CSRF: Origin no permitido: {origin}"
                )
                track_security_event(
                    'unauthorized_access',
                    labels={
                        'reason': 'invalid_origin',
                        'endpoint': path
                    }
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Origen no permitido"}
                )
    
    return await call_next(request)

# Content-Type Validation Middleware
@app.middleware("http")
async def content_type_validation_middleware(request: Request, call_next):
    """Middleware para validar Content-Type en requests."""
    if request.method in ("POST", "PUT", "PATCH"):
        content_type = request.headers.get("content-type", "")
        path = request.url.path
        
        # Endpoints que aceptan multipart/form-data (uploads)
        multipart_endpoints = ["/api/v1/candidates", "/upload", "/api/v1/roles/extract-from-document", "/api/v1/documents/extract-cv", "/api/v1/documents/upload"]
        
        # Si no es multipart, debe ser application/json
        if not any(path.startswith(ep) for ep in multipart_endpoints):
            if content_type and not content_type.startswith("application/json"):
                # Algunos clientes no envían Content-Type en GET/DELETE
                if request.method in ("POST", "PUT", "PATCH"):
                    await security_logger.log_unauthorized_access(
                        request,
                        f"Content-Type inválido: {content_type}"
                    )
                    return JSONResponse(
                        status_code=415,
                        content={"detail": "Content-Type debe ser application/json"}
                    )
    
    return await call_next(request)

# Rate Limiting Middleware (antes de CORS para proteger todos los endpoints)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    auth_requests_per_minute=5,
    login_requests_per_minute=3,
    password_reset_per_hour=1,
    candidates_post_per_minute=10,
    user_requests_per_minute=100,
)

# CSRF Protection Middleware (Double Submit Cookie pattern)
app.add_middleware(
    CSRFMiddleware,
    cookie_name="csrf_token",
    header_name="X-CSRF-Token",
    secure=settings.ENVIRONMENT == "production",
)

# CORS - FIX-003: Configuración restringida con valores explícitos
# Los orígenes se configuran desde variable de entorno CORS_ORIGINS
origins = settings.get_cors_origins()

# Validar que no haya wildcard con credentials
if "*" in origins and settings.ENVIRONMENT == "production":
    raise ValueError("CORS no puede usar '*' en producción con allow_credentials=True")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Trace-ID",
    ],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining", 
        "X-RateLimit-Reset",
        "X-Process-Time",
        "X-Trace-ID",
    ],
    max_age=600,
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware para agregar tiempo de procesamiento."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Routers
app.include_router(config.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
#app.include_router(candidates.router, prefix="/api/v1")  # Comentado - usando core_ats_router
app.include_router(evaluations.router, prefix="/api/v1")
app.include_router(matching.router, prefix="/api/v1")
app.include_router(rhtools.router, prefix="/api/v1")
app.include_router(health.router, prefix="")

# Core ATS API Router v1 (nuevo modelo de datos)
app.include_router(core_ats_router)

# Document Processing Pipeline Router
app.include_router(pipeline_router, prefix="/api/v1")

# Audit API Router (solo admin)
app.include_router(audit.router, prefix="/api/v1")

# Metrics API Router
app.include_router(metrics_api.router, prefix="")

# WhatsApp Webhook Router (sin prefix para webhook de Meta)
from app.api.whatsapp_webhook import router as whatsapp_webhook_router
app.include_router(whatsapp_webhook_router)


@app.get("/")
async def root():
    """Endpoint raíz."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/api/docs",
        "metrics": "/metrics"
    }


@app.get("/health")
async def health_check():
    """Endpoint de health check."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Manejador personalizado para errores de validación."""
    errors = exc.errors()
    
    # Verificar si es un error de UUID
    if is_uuid_validation_error(errors):
        param_name = extract_uuid_param_name(errors)
        await security_logger.log_unauthorized_access(
            request,
            f"UUID inválido en parámetro '{param_name}'"
        )
        return JSONResponse(
            status_code=400,
            content={
                "detail": f"UUID inválido en parámetro '{param_name}'. Debe ser un UUID válido",
                "error_code": "INVALID_UUID",
                "parameter": param_name
            }
        )
    
    # Para otros errores de validación
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Error de validación",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Manejador global de excepciones."""
    logger.error(f"Error no manejado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "error_code": "INTERNAL_ERROR",
            "path": str(request.url)
        }
    )
