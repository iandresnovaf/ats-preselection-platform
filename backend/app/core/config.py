from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache
from typing import Optional, List
import secrets


class Settings(BaseSettings):
    """Configuración de la aplicación."""
    
    # App
    APP_NAME: str = "ATS Preselection Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost/ats_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security - MUST be set in environment for production
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Encryption (Fernet key - 32 bytes base64 encoded)
    ENCRYPTION_KEY: Optional[str] = None
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB
    
    # Default Admin
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_PASSWORD: str = "changeme"
    
    # CORS - Orígenes permitidos (separados por coma)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # Allowed Hosts - para protección contra Host header attacks
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "*.localhost"]
    
    # API Keys (fallback si no hay config en BD)
    OPENAI_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_cors_origins(self) -> List[str]:
        """Obtiene lista de orígenes CORS permitidos."""
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        
        # En producción, nunca permitir wildcard
        if self.ENVIRONMENT == "production":
            origins = [o for o in origins if o != "*"]
            
        return origins
    
    @validator('SECRET_KEY')
    def validate_secret_key(cls, v, values):
        """Valida que SECRET_KEY sea seguro en producción."""
        environment = values.get('ENVIRONMENT', 'development')
        if environment == 'production':
            # En producción, el SECRET_KEY debe venir de environment
            # y tener al menos 32 caracteres
            if len(v) < 32:
                raise ValueError("SECRET_KEY debe tener al menos 32 caracteres en producción")
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
