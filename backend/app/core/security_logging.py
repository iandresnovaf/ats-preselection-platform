"""Logging de seguridad para auditoría y monitoreo."""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request


class SecurityLogger:
    """Logger especializado para eventos de seguridad."""
    
    def __init__(self):
        self.logger = logging.getLogger("security")
        self.logger.setLevel(logging.INFO)
        
        # Crear handler si no existe
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '[SECURITY] %(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _get_client_info(self, request: Request) -> Dict[str, Any]:
        """Extrae información del cliente de la request."""
        forwarded = request.headers.get("X-Forwarded-For")
        real_ip = request.headers.get("X-Real-IP")
        
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif real_ip:
            client_ip = real_ip
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return {
            "ip": client_ip,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "method": request.method,
            "path": str(request.url.path),
            "query_params": str(request.query_params),
        }
    
    def _log_event(
        self,
        event_type: str,
        message: str,
        request: Optional[Request] = None,
        user_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Registra un evento de seguridad."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "message": message,
            "user_id": user_id,
        }
        
        if request:
            event["client"] = self._get_client_info(request)
        
        if extra:
            event["extra"] = extra
        
        log_message = json.dumps(event, default=str)
        
        if event_type in ("login_failure", "unauthorized_access", "suspicious_activity"):
            self.logger.warning(log_message)
        elif event_type in ("security_breach", "data_exfiltration"):
            self.logger.error(log_message)
        else:
            self.logger.info(log_message)
    
    async def log_login_attempt(
        self,
        request: Request,
        email: str,
        success: bool,
        user_id: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """Loggear intento de login."""
        event_type = "login_success" if success else "login_failure"
        message = f"{'Login exitoso' if success else 'Login fallido'}: {email}"
        
        extra = {"email": email}
        if reason:
            extra["reason"] = reason
        
        self._log_event(event_type, message, request, user_id, extra)
    
    async def log_logout(
        self,
        request: Request,
        user_id: str
    ):
        """Loggear logout."""
        self._log_event(
            "logout",
            f"Usuario cerró sesión: {user_id}",
            request,
            user_id
        )
    
    async def log_unauthorized_access(
        self,
        request: Request,
        reason: str,
        user_id: Optional[str] = None
    ):
        """Loggear acceso no autorizado."""
        self._log_event(
            "unauthorized_access",
            f"Acceso no autorizado: {reason}",
            request,
            user_id,
            {"reason": reason}
        )
    
    async def log_password_change(
        self,
        request: Request,
        user_id: str,
        success: bool,
        reason: Optional[str] = None
    ):
        """Loggear cambio de contraseña."""
        event_type = "password_change_success" if success else "password_change_failure"
        message = f"{'Cambio' if success else 'Intento de cambio'} de contraseña"
        
        extra = {}
        if reason:
            extra["reason"] = reason
        
        self._log_event(event_type, message, request, user_id, extra)
    
    async def log_user_modification(
        self,
        request: Request,
        action: str,  # create, update, delete, status_change
        target_user_id: str,
        performed_by: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Loggear modificación de usuario."""
        self._log_event(
            "user_modification",
            f"Usuario {action}: {target_user_id}",
            request,
            performed_by,
            {
                "action": action,
                "target_user_id": target_user_id,
                "details": details
            }
        )
    
    async def log_config_change(
        self,
        request: Request,
        category: str,
        key: str,
        performed_by: str,
        old_value_masked: Optional[str] = None,
        new_value_masked: Optional[str] = None
    ):
        """Loggear cambio de configuración."""
        self._log_event(
            "config_change",
            f"Configuración modificada: {category}.{key}",
            request,
            performed_by,
            {
                "category": category,
                "key": key,
                "old_value_masked": old_value_masked,
                "new_value_masked": new_value_masked
            }
        )
    
    async def log_suspicious_activity(
        self,
        request: Request,
        activity_type: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Loggear actividad sospechosa."""
        self._log_event(
            "suspicious_activity",
            f"Actividad sospechosa detectada: {activity_type}",
            request,
            user_id,
            {"activity_type": activity_type, "details": details}
        )
    
    async def log_rate_limit_hit(
        self,
        request: Request,
        limit_type: str,
        retry_after: int
    ):
        """Loggear cuando se alcanza un rate limit."""
        self._log_event(
            "rate_limit_hit",
            f"Rate limit alcanzado: {limit_type}",
            request,
            extra={
                "limit_type": limit_type,
                "retry_after": retry_after
            }
        )
    
    async def log_token_refresh(
        self,
        request: Request,
        user_id: str,
        success: bool,
        reason: Optional[str] = None
    ):
        """Loggear refresh de token."""
        event_type = "token_refresh_success" if success else "token_refresh_failure"
        message = f"{'Refresh' if success else 'Intento de refresh'} de token"
        
        extra = {}
        if reason:
            extra["reason"] = reason
        
        self._log_event(event_type, message, request, user_id, extra)
