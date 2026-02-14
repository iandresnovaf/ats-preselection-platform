"""Logging estructurado en JSON para producción."""
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Contexto para trace_id y user_id
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class JSONFormatter(logging.Formatter):
    """Formatter que genera logs en formato JSON."""
    
    def __init__(self, service_name: str = "ats-platform"):
        super().__init__()
        self.service_name = service_name
        self.hostname = self._get_hostname()
    
    def _get_hostname(self) -> str:
        """Obtiene el hostname de la máquina."""
        import socket
        try:
            return socket.gethostname()
        except:
            return "unknown"
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatea el registro de log como JSON."""
        
        # Timestamp ISO8601
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Construir el objeto de log
        log_obj = {
            "timestamp": timestamp,
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
            "logger": record.name,
            "hostname": self.hostname,
        }
        
        # Agregar trace_id si existe en el contexto
        trace_id = trace_id_var.get()
        if trace_id:
            log_obj["trace_id"] = trace_id
        
        # Agregar user_id si existe en el contexto
        user_id = user_id_var.get()
        if user_id:
            log_obj["user_id"] = user_id
        
        # Agregar campos extra del record
        if hasattr(record, 'endpoint'):
            log_obj["endpoint"] = record.endpoint
        
        if hasattr(record, 'duration_ms'):
            log_obj["duration_ms"] = record.duration_ms
        
        if hasattr(record, 'method'):
            log_obj["method"] = record.method
        
        if hasattr(record, 'status_code'):
            log_obj["status_code"] = record.status_code
        
        # Agregar información de error si existe
        if record.exc_info:
            exc_type, exc_value, tb = record.exc_info
            log_obj["error"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
            }
        
        # Agregar cualquier campo extra personalizado
        if hasattr(record, 'extras'):
            log_obj.update(record.extras)
        
        return json.dumps(log_obj, ensure_ascii=False)


class StructuredLogger:
    """Logger estructurado con soporte para contexto."""
    
    def __init__(self, name: str, service_name: str = "ats-platform"):
        self.logger = logging.getLogger(name)
        self.service_name = service_name
    
    def _log(self, level: int, message: str, **kwargs):
        """Método interno para logging."""
        extra = {'extras': kwargs} if kwargs else {}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log de excepción con stack trace."""
        extra = {'extras': kwargs} if kwargs else {}
        self.logger.exception(message, extra=extra)


def configure_logging(
    level: str = "INFO",
    service_name: str = "ats-platform",
    json_format: bool = True
) -> None:
    """Configura el logging estructurado.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Nombre del servicio para identificación
        json_format: Si True, usa formato JSON. Si False, usa formato legible
    """
    # Limpiar handlers existentes
    root_logger = logging.getLogger()
    root_logger.handlers = []
    
    # Configurar nivel
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Handler para stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    
    if json_format:
        formatter = JSONFormatter(service_name=service_name)
    else:
        # Formato legible para desarrollo
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Reducir ruido de librerías de terceros
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """Setea o genera un trace_id para el contexto actual.
    
    Args:
        trace_id: ID de traza opcional. Si no se provee, se genera uno nuevo.
    
    Returns:
        El trace_id seteado
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())
    trace_id_var.set(trace_id)
    return trace_id


def get_trace_id() -> Optional[str]:
    """Obtiene el trace_id del contexto actual."""
    return trace_id_var.get()


def clear_trace_id():
    """Limpia el trace_id del contexto."""
    trace_id_var.set(None)


def set_user_id(user_id: Optional[str] = None):
    """Setea el user_id para el contexto actual."""
    user_id_var.set(user_id)


def get_user_id() -> Optional[str]:
    """Obtiene el user_id del contexto actual."""
    return user_id_var.get()


def clear_user_id():
    """Limpia el user_id del contexto."""
    user_id_var.set(None)


def get_logger(name: str) -> StructuredLogger:
    """Obtiene un logger estructurado."""
    return StructuredLogger(name)


# Middleware para FastAPI
async def logging_middleware(request, call_next):
    """Middleware que agrega trace_id y loguea requests."""
    from fastapi import Request
    import time
    
    # Generar trace_id
    trace_id = set_trace_id()
    
    # Extraer user_id del header si existe
    user_id = request.headers.get('X-User-ID')
    if user_id:
        set_user_id(user_id)
    
    # Log del request
    logger = get_logger("http")
    start_time = time.time()
    
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        method=request.method,
        endpoint=str(request.url.path),
        trace_id=trace_id,
        user_id=user_id
    )
    
    try:
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            method=request.method,
            endpoint=str(request.url.path),
            status_code=response.status_code,
            duration_ms=duration_ms,
            trace_id=trace_id,
            user_id=user_id
        )
        
        # Agregar trace_id al response header
        response.headers['X-Trace-ID'] = trace_id
        
        return response
        
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.exception(
            f"Request failed: {request.method} {request.url.path}",
            method=request.method,
            endpoint=str(request.url.path),
            duration_ms=duration_ms,
            trace_id=trace_id,
            user_id=user_id,
            error_type=type(exc).__name__
        )
        raise
        
    finally:
        clear_trace_id()
        clear_user_id()
