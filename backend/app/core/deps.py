"""Dependencias de FastAPI."""
import uuid
from typing import Union

from fastapi import Depends, HTTPException, status, Request, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import decode_token
from app.models import User, UserRole, UserStatus
from app.services.user_service import UserService

security = HTTPBearer(auto_error=False)


def validate_uuid(uuid_str: str) -> uuid.UUID:
    """
    Valida que un string sea un UUID válido.
    
    Args:
        uuid_str: String a validar
        
    Returns:
        UUID: Objeto UUID válido
        
    Raises:
        HTTPException: 400 si el UUID es inválido
    """
    try:
        return uuid.UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"UUID inválido: '{uuid_str}'. Debe ser un UUID válido (ej: 550e8400-e29b-41d4-a716-446655440000)"
        )


def validate_uuid_param(
    param_name: str = "id"
) -> Union[uuid.UUID, Path]:
    """
    Crea un Path parameter con validación de UUID.
    
    Usage:
        @router.get("/{candidate_id}")
        async def get_candidate(
            candidate_id: UUID = Depends(validate_uuid_param("candidate_id"))
        ):
            ...
    """
    return Path(..., description=f"ID en formato UUID")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Obtener usuario actual desde cookie httpOnly access_token o header Authorization."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Leer token de cookie httpOnly o del header Authorization
    token = request.cookies.get("access_token")
    if not token and credentials:
        token = credentials.credentials
    if not token:
        raise credentials_exception
    
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    token_type: str = payload.get("type")
    
    if user_id is None or token_type != "access":
        raise credentials_exception
    
    # Validar formato UUID
    try:
        uuid.UUID(user_id)
    except ValueError:
        raise credentials_exception
    
    # Buscar usuario
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verificar que el usuario está activo."""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Requerir rol de administrador (super_admin)."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return current_user


async def require_consultant(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Requerir rol de consultor o admin (puede crear/editar/eliminar)."""
    if current_user.role not in [UserRole.CONSULTANT, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de consultor",
        )
    return current_user


async def require_viewer(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Requerir rol de viewer, consultor o admin (solo lectura permitida).
    
    El rol VIEWER puede:
    - Ver jobs, candidates, submissions
    - NO puede crear/editar/eliminar
    """
    if current_user.role not in [UserRole.VIEWER, UserRole.CONSULTANT, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de visualización",
        )
    return current_user
