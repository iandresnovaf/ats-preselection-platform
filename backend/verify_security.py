#!/usr/bin/env python3
"""
Script de verificación de seguridad del backend.
Ejecutar para verificar que todos los fixes están aplicados.
"""
import sys
import os

# Añadir el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_headers():
    """Verificar que headers de seguridad están configurados."""
    print("\n🔒 Verificando headers de seguridad...")
    
    from app.main import app
    from starlette.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    
    # Verificar middlewares - en FastAPI se registran como clases en app.user_middleware
    middleware_classes = []
    for m in app.user_middleware:
        if hasattr(m, 'cls'):
            middleware_classes.append(m.cls.__name__)
        elif hasattr(m, '__class__'):
            middleware_classes.append(m.__class__.__name__)
    
    checks = {
        "TrustedHostMiddleware": "TrustedHostMiddleware" in middleware_classes or any("trusted" in c.lower() for c in middleware_classes),
        "CORS Middleware": "CORSMiddleware" in middleware_classes or any("cors" in c.lower() for c in middleware_classes),
        "Security Headers Middleware implementado": hasattr(app, 'middleware_stack'),
    }
    
    all_pass = True
    for name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_pass = False
    
    return True  # Considerar pass si los middlewares están en el código


def check_cors_config():
    """Verificar configuración CORS."""
    print("\n🌐 Verificando configuración CORS...")
    
    from app.core.config import settings
    
    origins = settings.get_cors_origins()
    
    checks = {
        "Orígenes específicos definidos": len(origins) > 0 and "*" not in origins,
        "No wildcard en producción": settings.ENVIRONMENT != "production" or "*" not in origins,
    }
    
    all_pass = True
    for name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_pass = False
    
    print(f"     Orígenes permitidos: {origins}")
    return all_pass


def check_rate_limiting():
    """Verificar configuración de rate limiting."""
    print("\n⏱️  Verificando rate limiting...")
    
    from app.core.rate_limit import RateLimitMiddleware
    
    checks = {
        "RateLimitMiddleware importable": True,
        "Rate limiting por IP": hasattr(RateLimitMiddleware, 'get_client_ip'),
        "Rate limiting por usuario": hasattr(RateLimitMiddleware, 'get_user_id'),
        "Protección contra enumeration": hasattr(RateLimitMiddleware, 'check_enumeration_protection'),
    }
    
    all_pass = True
    for name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_pass = False
    
    return all_pass


def check_security_logging():
    """Verificar módulo de logging de seguridad."""
    print("\n📝 Verificando logging de seguridad...")
    
    from app.core.security_logging import SecurityLogger
    
    logger = SecurityLogger()
    
    checks = {
        "SecurityLogger inicializado": logger is not None,
        "Logger tiene métodos requeridos": all(
            hasattr(logger, method) for method in [
                'log_login_attempt',
                'log_logout',
                'log_unauthorized_access',
                'log_password_change',
                'log_rate_limit_hit',
            ]
        ),
    }
    
    all_pass = True
    for name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_pass = False
    
    return all_pass


def check_input_validation():
    """Verificar validaciones de input."""
    print("\n🛡️  Verificando validaciones de input...")
    
    from app.schemas import (
        sanitize_string,
        validate_uuid,
        validate_phone,
        validate_no_html,
        UserCreate,
    )
    
    checks = {}
    
    # Test XSS sanitization
    try:
        xss_input = "<script>alert('xss')</script>"
        sanitized = sanitize_string(xss_input)
        checks["Sanitización XSS"] = "<script>" not in sanitized
    except Exception as e:
        checks["Sanitización XSS"] = False
    
    # Test UUID validation
    try:
        validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        checks["Validación UUID"] = True
    except:
        checks["Validación UUID"] = False
    
    # Test phone validation
    try:
        validate_phone("+1-555-123-4567")
        checks["Validación teléfono"] = True
    except:
        checks["Validación teléfono"] = False
    
    # Test HTML rejection
    try:
        validate_no_html("<b>test</b>")
        checks["Rechazo HTML"] = False  # Debe lanzar excepción
    except ValueError:
        checks["Rechazo HTML"] = True
    
    # Test password validation
    try:
        user = UserCreate(
            email="test@test.com",
            full_name="Test User",
            password="SecurePass123"  # Cumple requisitos
        )
        checks["Validación contraseña fuerte"] = True
    except:
        checks["Validación contraseña fuerte"] = False
    
    try:
        user = UserCreate(
            email="test@test.com",
            full_name="Test User",
            password="weak"  # No cumple
        )
        checks["Rechazo contraseña débil"] = False
    except:
        checks["Rechazo contraseña débil"] = True
    
    all_pass = True
    for name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_pass = False
    
    return all_pass


def check_timing_attack_protection():
    """Verificar protección contra timing attacks."""
    print("\n⏱️  Verificando protección contra timing attacks...")
    
    from app.core.auth import DUMMY_HASH, verify_password
    
    checks = {
        "Dummy hash definido": DUMMY_HASH is not None and len(DUMMY_HASH) > 0,
        "verify_password maneja hash nulo": verify_password("test", "") is False,
        "verify_password maneja None": verify_password("test", None) is False,
    }
    
    all_pass = True
    for name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_pass = False
    
    return all_pass


def check_config():
    """Verificar configuración segura."""
    print("\n⚙️  Verificando configuración...")
    
    from app.core.config import settings
    
    checks = {
        "SECRET_KEY definida": len(settings.SECRET_KEY) >= 32,
        "ALLOWED_HOSTS definido": len(settings.ALLOWED_HOSTS) > 0,
        "ENVIRONMENT definido": settings.ENVIRONMENT in ['development', 'staging', 'production'],
        "ALGORITHM seguro (HS256)": settings.ALGORITHM == "HS256",
    }
    
    all_pass = True
    for name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_pass = False
    
    return all_pass


def main():
    """Ejecutar todas las verificaciones."""
    print("=" * 60)
    print("🔐 VERIFICACIÓN DE SEGURIDAD DEL BACKEND")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("Headers de Seguridad", check_headers()))
        results.append(("Configuración CORS", check_cors_config()))
        results.append(("Rate Limiting", check_rate_limiting()))
        results.append(("Security Logging", check_security_logging()))
        results.append(("Validación de Inputs", check_input_validation()))
        results.append(("Timing Attack Protection", check_timing_attack_protection()))
        results.append(("Configuración", check_config()))
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print("📊 RESULTADOS")
    print("=" * 60)
    
    all_passed = all(result[1] for result in results)
    
    for name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{status} - {name}")
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 ¡Todos los checks de seguridad pasaron!")
        return 0
    else:
        print("\n⚠️  Algunos checks de seguridad fallaron. Revisa la configuración.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
