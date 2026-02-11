"""API endpoints de autenticación."""
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/login", response_model=Token)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login con email y password."""
    user = await authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
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
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token."""
    payload = decode_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    
    # Verificar que el usuario existe y está activo
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user or user.status.value != "active":
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
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/logout", response_model=MessageResponse)
async def logout(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Logout - revoca el refresh token."""
    # En una implementación completa, agregaríamos el token a una blacklist en Redis
    # Por ahora, solo validamos que el token sea válido
    payload = decode_token(refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    
    return {"message": "Logout exitoso", "success": True}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Obtener información del usuario actual."""
    from app.core.deps import get_current_user
    
    user = await get_current_user(credentials, db)
    return user


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: PasswordChange,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Cambiar password del usuario actual."""
    from app.core.deps import get_current_user
    
    user = await get_current_user(credentials, db)
    
    # Verificar password actual
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password actual incorrecto",
        )
    
    # Actualizar password
    user_service = UserService(db)
    await user_service.update_password(str(user.id), data.new_password)
    
    return {"message": "Password cambiado exitosamente", "success": True}


@router.post("/change-email", response_model=MessageResponse)
async def change_email(
    data: EmailChange,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Cambiar email del usuario actual."""
    from app.core.deps import get_current_user
    
    user = await get_current_user(credentials, db)
    
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
