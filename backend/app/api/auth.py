"""API endpoints de autenticación con logging de seguridad y rate limiting."""
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    decode_token,
)
from app.core.security_logging import SecurityLogger
from app.schemas import (
    LoginRequest,
    Token,
    UserResponse,
    PasswordChange,
    EmailChange,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from app.services.user_service import UserService

# Logger de seguridad
security_logger = SecurityLogger()

# Rate Limiter - 5 intentos por minuto para auth
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

# Cookie settings - secure=True en producción
COOKIE_SETTINGS = {
    "httponly": True,
    "secure": settings.ENVIRONMENT == "production",
    "samesite": "strict" if settings.ENVIRONMENT == "production" else "lax",
    "path": "/",
}


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Login con email y password. Setea cookies httpOnly."""
    user = await authenticate_user(
        db, 
        credentials.email, 
        credentials.password,
        request=request
    )
    
    if not user:
        # Respuesta genérica para prevenir user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacte al administrador.",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Setear cookies httpOnly
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **COOKIE_SETTINGS
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **COOKIE_SETTINGS
    )
    
    return {
        "success": True,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "status": user.status.value,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }
    }


@router.post("/register")
@limiter.limit("5/minute")
async def register(
    request: Request,
    credentials: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Registrar nuevo usuario. Setea cookies httpOnly."""
    user_service = UserService(db)
    
    # Verificar si el email ya existe
    existing = await user_service.get_by_email(credentials.email)
    if existing:
        # Respuesta genérica para prevenir user enumeration
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo completar el registro",
        )
    
    # Crear usuario
    from app.schemas import UserCreate
    user_data = UserCreate(
        email=credentials.email,
        password=credentials.password,
        full_name=credentials.email.split('@')[0],  # Nombre temporal
        role="consultant"
    )
    
    try:
        user = await user_service.create_user(user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Generar tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Setear cookies httpOnly
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **COOKIE_SETTINGS
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **COOKIE_SETTINGS
    )
    
    return {
        "success": True,
        "message": "Usuario registrado exitosamente",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "status": user.status.value,
        }
    }


@router.post("/refresh")
@limiter.limit("5/minute")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token. Lee refresh_token de cookie y setea nueva access_token cookie."""
    refresh_token_str = request.cookies.get("refresh_token")
    
    if not refresh_token_str:
        await security_logger.log_token_refresh(
            request, "unknown", success=False, reason="No refresh token in cookie"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token no encontrado",
        )
    
    payload = decode_token(refresh_token_str)
    
    if not payload or payload.get("type") != "refresh":
        await security_logger.log_token_refresh(
            request, "unknown", success=False, reason="Token inválido o no es refresh token"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        await security_logger.log_token_refresh(
            request, "unknown", success=False, reason="Token sin user_id"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    
    # Verificar que el usuario existe y está activo
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user or user.status.value != "active":
        await security_logger.log_token_refresh(
            request, user_id, success=False, reason="Usuario no encontrado o inactivo"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )
    
    # Crear nuevos tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Setear nuevas cookies
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **COOKIE_SETTINGS
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **COOKIE_SETTINGS
    )
    
    await security_logger.log_token_refresh(request, user_id, success=True)
    
    return {"success": True}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Logout - limpia las cookies httpOnly."""
    # Leer refresh_token de cookie para logging
    refresh_token_str = request.cookies.get("refresh_token")
    
    if refresh_token_str:
        payload = decode_token(refresh_token_str)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                await security_logger.log_logout(request, user_id)
    
    # Limpiar cookies
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    
    return {"message": "Logout exitoso", "success": True}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Obtener información del usuario actual desde cookie."""
    from app.core.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    return user


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: PasswordChange,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Cambiar password del usuario actual."""
    from app.core.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    
    # Verificar password actual
    if not verify_password(data.current_password, user.hashed_password):
        await security_logger.log_password_change(
            request, str(user.id), success=False, reason="Contraseña actual incorrecta"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password actual incorrecto",
        )
    
    # Actualizar password
    user_service = UserService(db)
    await user_service.update_password(str(user.id), data.new_password)
    
    await security_logger.log_password_change(request, str(user.id), success=True)
    
    return {"message": "Password cambiado exitosamente", "success": True}


@router.post("/change-email", response_model=MessageResponse)
async def change_email(
    data: EmailChange,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Cambiar email del usuario actual."""
    from app.core.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    
    # Verificar password
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password incorrecto",
        )
    
    # Verificar que el nuevo email no esté en uso
    user_service = UserService(db)
    existing = await user_service.get_by_email(data.new_email)
    if existing and existing.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está en uso por otro usuario",
        )
    
    # Actualizar email
    await user_service.update(str(user.id), {"email": data.new_email})
    
    return {"message": "Email cambiado exitosamente", "success": True}


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Solicitar recuperación de contraseña."""
    user_service = UserService(db)
    user = await user_service.get_by_email(data.email)
    
    # No revelar si el email existe (seguridad)
    if not user:
        return {"message": "Si el email existe, recibirás instrucciones para recuperar tu contraseña", "success": True}
    
    # Generar token de reseteo (válido por 1 hora)
    reset_token = create_access_token(
        data={"sub": str(user.id), "type": "reset_password"},
        expires_delta=timedelta(hours=1),
    )
    
    # TODO: Enviar email con el token
    # Por ahora solo logueamos el token (en producción se enviaría por email)
    print(f"[PASSWORD RESET] Token para {data.email}: {reset_token}")
    
    return {"message": "Si el email existe, recibirás instrucciones para recuperar tu contraseña", "success": True}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Resetear contraseña con token."""
    payload = decode_token(data.token)
    
    if not payload or payload.get("type") != "reset_password":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido",
        )
    
    # Verificar que el usuario existe
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user or user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario no encontrado o inactivo",
        )
    
    # Actualizar password
    await user_service.update_password(user_id, data.new_password)
    
    return {"message": "Contraseña actualizada exitosamente", "success": True}
