"""Base de datos y sesiones."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import TypeDecorator, Text
from typing import Optional

from app.core.config import settings
from app.core.security import encryption_manager

# Convertir URL sync a async
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Configurar conexiones SSL/TLS
# El parámetro ssl=require fuerza conexiones cifradas
connect_args = {}
if "?ssl=require" in DATABASE_URL or "&ssl=require" in DATABASE_URL:
    # ssl=require ya está en la URL
    pass
else:
    # Añadir parámetros SSL por defecto en producción
    if settings.ENVIRONMENT == "production":
        if "?" in DATABASE_URL:
            DATABASE_URL = f"{DATABASE_URL}&ssl=require"
        else:
            DATABASE_URL = f"{DATABASE_URL}?ssl=require"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,              # Conexiones mantenidas permanentemente
    max_overflow=20,           # Conexiones adicionales bajo carga
    pool_timeout=30,           # Segundos esperando conexión disponible
    pool_recycle=1800,         # Reciclar conexiones cada 30 minutos
    echo=settings.DEBUG,
    future=True,
    # Configuración de SSL solo en producción
    connect_args={
        "ssl": True,
        "server_settings": {
            "jit": "off",  # Desactivar JIT para evitar problemas de compatibilidad
        }
    } if settings.ENVIRONMENT == "production" else {}
)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


class EncryptedType(TypeDecorator):
    """
    Tipo de columna SQLAlchemy que encripta/desencripta automáticamente.
    
    Uso:
        email = Column(EncryptedType)
        phone = Column(EncryptedType)
    """
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encriptar antes de guardar en BD."""
        if value is None:
            return None
        return encryption_manager.encrypt(str(value))
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Desencriptar al leer de BD."""
        if value is None:
            return None
        try:
            return encryption_manager.decrypt(str(value))
        except Exception:
            # Si falla el desencriptado, podría ser un valor plano (migración)
            return value


class EncryptedJSON(TypeDecorator):
    """
    Tipo de columna SQLAlchemy que encripta JSON como string.
    
    Uso para datos PII en campos JSON.
    """
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encriptar antes de guardar en BD."""
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            import json
            value = json.dumps(value)
        return encryption_manager.encrypt(str(value))
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Desencriptar al leer de BD."""
        if value is None:
            return None
        try:
            decrypted = encryption_manager.decrypt(str(value))
            return decrypted
        except Exception:
            return value


async def get_db():
    """Dependency para obtener sesión de BD."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection():
    """Verificar conexión a la base de datos."""
    from sqlalchemy import text
    async with async_session_maker() as session:
        result = await session.execute(text("SELECT 1"))
        return result.scalar() == 1
