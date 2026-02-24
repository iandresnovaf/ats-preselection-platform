"""Autenticación JWT con protección contra timing attacks."""
import secrets
import uuid as uuid_module
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.token_blacklist import token_blacklist

# Import directo para evitar circular imports
# User y UserStatus se importan localmente donde se usan

# Password hashing con bcrypt y timing attack protection
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=12  # Cost factor recomendado (12-14)
)

# JWT
security = HTTPBearer()

# Dummy hash para timing attack protection - se genera bajo demanda
# para evitar problemas de inicialización con bcrypt
def get_dummy_hash():
    """Genera un hash dummy para timing attack protection."""
    return pwd_context.hash("dummy_pass")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar password contra hash con protección contra timing attacks.
    
    Usa constant-time comparison para prevenir ataques de temporización.
    """
    if not hashed_password:
        # Si no hay hash, verificar contra dummy para mantener tiempo constante
        pwd_context.verify(plain_password, get_dummy_hash())
        return False
    
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def verify_password_constant_time(plain_password: str, hashed_password: str) -> bool:
    """
    Verificación de password con comparación en tiempo constante.
    Previene timing attacks al hacer que todas las operaciones tomen el mismo tiempo.
    """
    # Siempre realizar una verificación de bcrypt (lento) para mantener tiempo constante
    if not hashed_password:
        # Verificar contra dummy hash
        pwd_context.verify(plain_password, get_dummy_hash())
        return False
    
    result = pwd_context.verify(plain_password, hashed_password)
    return result


def get_password_hash(password: str) -> str:
    """Generar hash de password usando bcrypt con salt automático."""
    return pwd_context.hash(password)


def generate_secure_token(length: int = 32) -> str:
    """Genera un token seguro usando secrets (criptográficamente seguro)."""
    return secrets.token_urlsafe(length)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crear token JWT de acceso con JTI para invalidación."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Generar JTI único para poder invalidar el token
    jti = str(uuid_module.uuid4())
    
    to_encode.update({
        "exp": expire, 
        "type": "access",
        "jti": jti,
        "iat": datetime.utcnow()
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Crear token JWT de refresh con JTI para invalidación."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Generar JTI único
    jti = str(uuid_module.uuid4())
    
    to_encode.update({
        "exp": expire, 
        "type": "refresh",
        "jti": jti,
        "iat": datetime.utcnow()
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decodificar y validar token JWT."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except PyJWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Obtener usuario actual desde token JWT (header Authorization - legacy)."""
    from app.models import User, UserStatus
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    token_type: str = payload.get("type")
    token_jti: str = payload.get("jti")
    token_iat = payload.get("iat")
    
    if user_id is None or token_type != "access":
        raise credentials_exception
    
    # Verificar si el token está en la blacklist
    if token_jti:
        is_blacklisted = await token_blacklist.is_blacklisted(token_jti)
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalidado",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Buscar usuario
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # Verificar si el usuario fue revocado globalmente
    iat_datetime = datetime.fromtimestamp(token_iat) if token_iat else None
    is_revoked = await token_blacklist.is_user_revoked(user_id, iat_datetime)
    if is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión revocada. Por favor inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    return user


async def get_current_user_from_cookie(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Obtener usuario actual desde cookie httpOnly access_token."""
    from app.models import User, UserStatus
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Leer token de cookie
    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception
    
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    token_type: str = payload.get("type")
    token_jti: str = payload.get("jti")
    token_iat = payload.get("iat")
    
    if user_id is None or token_type != "access":
        raise credentials_exception
    
    # Verificar si el token está en la blacklist
    if token_jti:
        is_blacklisted = await token_blacklist.is_blacklisted(token_jti)
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalidado",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Buscar usuario
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # Verificar si el usuario fue revocado globalmente
    iat_datetime = datetime.fromtimestamp(token_iat) if token_iat else None
    is_revoked = await token_blacklist.is_user_revoked(user_id, iat_datetime)
    if is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión revocada. Por favor inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    return user


async def authenticate_user(
    db: AsyncSession, 
    email: str, 
    password: str,
    request=None  # Para logging de seguridad
):
    """
    Autenticar usuario con email y password.
    
    Implementa protección contra timing attacks:
    - Siempre realiza hash verification (incluso si usuario no existe)
    - Usa dummy hash para mantener tiempo constante
    """
    from app.models import User, UserStatus
    from app.core.security_logging import SecurityLogger
    security_logger = SecurityLogger()
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Realizar verificación contra dummy hash para timing attack protection
        verify_password(password, DUMMY_HASH)
        
        # Loggear intento fallido
        if request:
            await security_logger.log_login_attempt(
                request, email, success=False, reason="Usuario no encontrado"
            )
        return None
    
    # Verificar password
    if not verify_password(password, user.hashed_password):
        # Loggear intento fallido
        if request:
            await security_logger.log_login_attempt(
                request, email, success=False, user_id=str(user.id), reason="Contraseña incorrecta"
            )
        return None
    
    # Verificar que el usuario esté activo
    if user.status != UserStatus.ACTIVE:
        if request:
            await security_logger.log_login_attempt(
                request, email, success=False, user_id=str(user.id), reason="Usuario inactivo"
            )
        return None
    
    # Actualizar último login
    user.last_login = datetime.utcnow()
    await db.flush()
    
    # Loggear login exitoso
    if request:
        await security_logger.log_login_attempt(
            request, email, success=True, user_id=str(user.id)
        )
    
    return user
