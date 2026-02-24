"""
CSRF Protection usando Double Submit Cookie pattern.
Protege contra ataques Cross-Site Request Forgery.
"""
import secrets
import hashlib
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware para protección CSRF usando Double Submit Cookie pattern.
    
    Este patrón:
    1. Envía un token CSRF en una cookie (no httpOnly para que JS pueda leerla)
    2. El frontend debe enviar el mismo token en el header X-CSRF-Token
    3. El servidor compara ambos valores
    
    Esto protege contra CSRF porque:
    - Un atacante no puede leer la cookie CSRF (same-origin policy)
    - Por lo tanto no puede enviar el header X-CSRF-Token correcto
    """
    
    def __init__(
        self,
        app,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        secure: bool = True,
        exempt_paths: Optional[list] = None,
        exempt_methods: Optional[set] = None
    ):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.secure = secure if settings.ENVIRONMENT == "production" else False
        self.exempt_paths = exempt_paths or [
            "/api/v1/auth/login",
            "/api/v1/auth/login/mfa",
            "/api/v1/auth/register",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/refresh",
            "/api/v1/auth/logout",
            "/api/v1/auth/mfa/setup",
            "/api/v1/auth/mfa/verify",
        ]
        self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS", "TRACE"}
    
    def is_exempt(self, request: Request) -> bool:
        """Verifica si el request está exento de CSRF."""
        # Métodos seguros no requieren CSRF
        if request.method in self.exempt_methods:
            return True
        
        # Paths exentos
        path = request.url.path
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        
        return False
    
    def generate_csrf_token(self) -> str:
        """Genera un token CSRF seguro."""
        return secrets.token_urlsafe(32)
    
    def get_csrf_cookie(self, request: Request) -> Optional[str]:
        """Obtiene el token CSRF de la cookie."""
        return request.cookies.get(self.cookie_name)
    
    def get_csrf_header(self, request: Request) -> Optional[str]:
        """Obtiene el token CSRF del header."""
        return request.headers.get(self.header_name)
    
    def validate_csrf_token(self, cookie_token: str, header_token: str) -> bool:
        """Valida que los tokens coincidan."""
        if not cookie_token or not header_token:
            return False
        
        # Comparación segura en tiempo constante
        return secrets.compare_digest(cookie_token, header_token)
    
    async def dispatch(self, request: Request, call_next):
        # Si está exento, continuar normalmente
        if self.is_exempt(request):
            response = await call_next(request)
            
            # Si no hay cookie CSRF, generar una
            if self.cookie_name not in request.cookies and request.method == "GET":
                csrf_token = self.generate_csrf_token()
                response.set_cookie(
                    key=self.cookie_name,
                    value=csrf_token,
                    max_age=365 * 24 * 60 * 60,  # 1 año
                    path="/",
                    secure=self.secure,
                    httponly=False,  # Debe ser accesible por JS
                    samesite="strict" if settings.ENVIRONMENT == "production" else "lax"
                )
            
            return response
        
        # Validar CSRF para métodos no seguros
        cookie_token = self.get_csrf_cookie(request)
        header_token = self.get_csrf_header(request)
        
        if not self.validate_csrf_token(cookie_token, header_token):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF token inválido o faltante",
                    "code": "CSRF_ERROR"
                }
            )
        
        # Continuar con el request
        response = await call_next(request)
        return response


class CSRFProtector:
    """Utilidad para proteger endpoints específicos con CSRF."""
    
    @staticmethod
    def validate_request(request: Request, cookie_name: str = "csrf_token", header_name: str = "X-CSRF-Token"):
        """Valida CSRF para un request específico."""
        cookie_token = request.cookies.get(cookie_name)
        header_token = request.headers.get(header_name)
        
        if not cookie_token or not header_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token faltante"
            )
        
        if not secrets.compare_digest(cookie_token, header_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token inválido"
            )


def generate_csrf_token() -> str:
    """Genera un token CSRF."""
    return secrets.token_urlsafe(32)
