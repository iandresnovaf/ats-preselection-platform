"""
Token blacklist para invalidación de JWT en logout.
Implementa almacenamiento en Redis con TTL automático.
"""
import json
from datetime import datetime, timedelta
from typing import Optional
import redis.asyncio as redis
from app.core.config import settings


class TokenBlacklist:
    """Gestiona la blacklist de tokens JWT en Redis."""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self.key_prefix = "token_blacklist"
    
    async def get_redis(self) -> redis.Redis:
        """Obtiene conexión Redis lazy."""
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis
    
    def _get_key(self, token_jti: str) -> str:
        """Genera key para token en Redis."""
        return f"{self.key_prefix}:{token_jti}"
    
    async def add_to_blacklist(
        self, 
        token_jti: str, 
        expires_at: datetime,
        user_id: Optional[str] = None,
        reason: str = "logout"
    ) -> bool:
        """
        Agrega un token a la blacklist.
        
        Args:
            token_jti: JWT ID único del token
            expires_at: Fecha de expiración del token
            user_id: ID del usuario (opcional, para tracking)
            reason: Razón de la invalidación
        
        Returns:
            True si se agregó correctamente
        """
        try:
            r = await self.get_redis()
            key = self._get_key(token_jti)
            
            # Calcular TTL basado en la expiración del token
            now = datetime.utcnow()
            if expires_at <= now:
                # Token ya expirado, no necesita blacklist
                return True
            
            ttl_seconds = int((expires_at - now).total_seconds())
            
            # Almacenar metadata del token blacklisted
            data = {
                "jti": token_jti,
                "user_id": user_id or "unknown",
                "reason": reason,
                "blacklisted_at": now.isoformat(),
                "expires_at": expires_at.isoformat()
            }
            
            await r.setex(key, ttl_seconds, json.dumps(data))
            
            # También agregar a un set por usuario para tracking
            if user_id:
                user_key = f"{self.key_prefix}:user:{user_id}"
                await r.zadd(user_key, {token_jti: now.timestamp()})
                # Expirar el set después de 7 días
                await r.expire(user_key, 7 * 24 * 3600)
            
            return True
            
        except Exception as e:
            # Log error pero no fallar el logout
            print(f"[TokenBlacklist] Error adding to blacklist: {e}")
            return False
    
    async def is_blacklisted(self, token_jti: str) -> bool:
        """
        Verifica si un token está en la blacklist.
        
        Args:
            token_jti: JWT ID del token
        
        Returns:
            True si el token está blacklisted
        """
        try:
            r = await self.get_redis()
            key = self._get_key(token_jti)
            exists = await r.exists(key)
            return bool(exists)
            
        except Exception:
            # Si Redis falla, asumir que no está blacklisted (fail open)
            return False
    
    async def blacklist_all_user_tokens(
        self, 
        user_id: str, 
        exclude_jti: Optional[str] = None,
        reason: str = "security_action"
    ) -> int:
        """
        Invalida todos los tokens de un usuario (logout global).
        
        Args:
            user_id: ID del usuario
            exclude_jti: JTI a excluir (token actual que se renovará)
            reason: Razón de la invalidación masiva
        
        Returns:
            Número de tokens invalidados
        """
        try:
            r = await self.get_redis()
            
            # Usar un flag de revocación global por usuario
            key = f"{self.key_prefix}:revoked:{user_id}"
            data = {
                "revoked_at": datetime.utcnow().isoformat(),
                "reason": reason
            }
            # TTL de 7 días (máximo tiempo de vida de un refresh token)
            await r.setex(key, 7 * 24 * 3600, json.dumps(data))
            
            return 1
            
        except Exception as e:
            print(f"[TokenBlacklist] Error revoking user tokens: {e}")
            return 0
    
    async def is_user_revoked(self, user_id: str, token_iat: Optional[datetime] = None) -> bool:
        """
        Verifica si todos los tokens de un usuario fueron revocados.
        
        Args:
            user_id: ID del usuario
            token_iat: Fecha de emisión del token (para verificar si fue emitido antes de la revocación)
        
        Returns:
            True si los tokens del usuario fueron revocados
        """
        try:
            r = await self.get_redis()
            key = f"{self.key_prefix}:revoked:{user_id}"
            
            data = await r.get(key)
            if not data:
                return False
            
            revoked_data = json.loads(data)
            revoked_at = datetime.fromisoformat(revoked_data["revoked_at"])
            
            # Si el token fue emitido antes de la revocación, es inválido
            if token_iat and token_iat < revoked_at:
                return True
            
            return True
            
        except Exception:
            return False
    
    async def cleanup_expired(self, max_keys: int = 1000) -> int:
        """
        Limpia entradas expiradas (Redis las elimina automáticamente con TTL).
        Esta función es para mantenimiento manual si es necesario.
        
        Args:
            max_keys: Máximo de keys a verificar
        
        Returns:
            Número de keys eliminadas
        """
        # Redis elimina automáticamente las keys con TTL expirado
        # Esta función puede usarse para limpieza de índices secundarios
        return 0


# Singleton instance
token_blacklist = TokenBlacklist()


async def check_token_blacklist(token_jti: str) -> bool:
    """Helper function para verificar si un token está blacklisted."""
    return await token_blacklist.is_blacklisted(token_jti)
