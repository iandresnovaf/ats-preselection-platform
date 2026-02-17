"""Aplicación FastAPI principal."""
import re
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine, Base
from app.core.rate_limit import RateLimitMiddleware
from app.core.security_logging import SecurityLogger
from app.api import config, auth, users, jobs, candidates, evaluations, matching, health, rhtools
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo del ciclo de vida de la aplicación."""
    # Startup
    print("🚀 Starting ATS Platform...")
    logger.info("Iniciando ATS Platform...")
    
    # Crear tablas (en desarrollo)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database tables created")
    logger.info("Tablas de base de datos creadas")
    
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

# Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Middleware para agregar headers de seguridad HTTP."""
    response = await call_next(request)
    
    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "media-src 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
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
    
    return response

# CSRF Protection Middleware
@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    """Middleware para protección CSRF."""
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
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Content-Type no válido"}
                    )
            
            # Verificar Origin/Referer para SameSite protection
            origin = request.headers.get("origin", "")
            referer = request.headers.get("referer", "")
            
            allowed_origins = settings.get_cors_origins()
            
            # Si hay Origin header, debe coincidir con allowed origins
            if origin and origin not in allowed_origins:
                await security_logger.log_unauthorized_access(
                    request,
                    f"CSRF: Origin no permitido: {origin}"
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
        multipart_endpoints = ["/api/v1/candidates", "/upload"]
        
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
)

# CORS - FIX-003: Configuración restringida con valores explícitos
# Los orígenes se configuran desde variable de entorno CORS_ORIGINS
origins = settings.get_cors_origins()

# Validar que no haya wildcard con credentials
if "*" in origins and settings.ENVIRONMENT == "production":
    raise ValueError("CORS no puede usar '*' en producción con allow_credentials=True")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Orígenes permitidos desde variable de entorno
    allow_credentials=True,  # Importante: permite envío de cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],  # FIX-003: Métodos explícitos
    allow_headers=[  # FIX-003: Headers explícitos (no "*")
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
    expose_headers=[  # Headers expuestos al cliente
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining", 
        "X-RateLimit-Reset",
        "X-Process-Time",
    ],
    max_age=600,  # Cache preflight por 10 minutos
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
app.include_router(candidates.router, prefix="/api/v1")
app.include_router(evaluations.router, prefix="/api/v1")
app.include_router(matching.router, prefix="/api/v1")
app.include_router(rhtools.router, prefix="/api/v1")
app.include_router(health.router, prefix="")

# Core ATS API Router v1 (nuevo modelo de datos)
app.include_router(core_ats_router)

# Document Processing Pipeline Router
app.include_router(pipeline_router, prefix="/api/v1")

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
        "docs": "/api/docs"
    }


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
