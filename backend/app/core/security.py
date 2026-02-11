"""Utilidades de cifrado para credenciales."""
from cryptography.fernet import Fernet
from typing import Optional
import base64
import hashlib

from app.core.config import settings


class EncryptionManager:
    """Gestiona el cifrado/descifrado de credenciales sensibles."""
    
    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._init_cipher()
    
    def _init_cipher(self):
        """Inicializa el cipher Fernet."""
        key = settings.ENCRYPTION_KEY
        if not key:
            # Generar key derivada del SECRET_KEY (solo para desarrollo)
            key = base64.urlsafe_b64encode(
                hashlib.sha256(settings.SECRET_KEY.encode()).digest()[:32]
            ).decode()
        
        # Asegurar que la key sea válida para Fernet (32 bytes base64 encoded)
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception:
            # Si la key no es válida, derivar una nueva
            derived_key = base64.urlsafe_b64encode(
                hashlib.sha256(settings.SECRET_KEY.encode()).digest()[:32]
            )
            self._fernet = Fernet(derived_key)
    
    def encrypt(self, value: str) -> str:
        """Cifra un valor string."""
        if not value:
            return ""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.encrypt(value.encode()).decode()
    
    def decrypt(self, encrypted_value: str) -> str:
        """Descifra un valor string."""
        if not encrypted_value:
            return ""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        try:
            return self._fernet.decrypt(encrypted_value.encode()).decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt value: {e}")


# Singleton
encryption_manager = EncryptionManager()


def encrypt_value(value: str) -> str:
    """Cifra un valor."""
    return encryption_manager.encrypt(value)


def decrypt_value(encrypted_value: str) -> str:
    """Descifra un valor."""
    return encryption_manager.decrypt(encrypted_value)
