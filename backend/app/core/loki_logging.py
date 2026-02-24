"""
Integración con Loki para logs centralizados (OPCIONAL).
Handler personalizado para enviar logs a Loki.

Este módulo puede funcionar sin Loki configurado.
Set LOKI_ENABLED=false para usar solo logging a consola/archivo.
"""
import json
import logging
import os
import sys
import queue
import threading
import time
from typing import Optional, Dict, Any
from datetime import datetime

# Logger para este módulo
logger = logging.getLogger(__name__)

# Verificar si Loki está habilitado
LOKI_ENABLED = os.getenv("LOKI_ENABLED", "true").lower() == "true"

# Intentar importar requests, pero no fallar si no está
try:
    import requests
    _requests_available = True
except ImportError:
    logger.warning("requests no disponible. Loki logging deshabilitado.")
    _requests_available = False
    requests = None


class LokiHandler(logging.Handler):
    """
    Handler de logging que envía logs a Grafana Loki.
    Implementa buffering y reintentos para no bloquear la aplicación.
    
    Si Loki no está disponible o está deshabilitado, los logs se descartan silenciosamente
    o se reenvían al handler de consola si está configurado.
    """
    
    def __init__(
        self,
        url: str = "http://localhost:3100",
        labels: Optional[Dict[str, str]] = None,
        buffer_size: int = 100,
        flush_interval: float = 5.0,
        timeout: int = 5
    ):
        """
        Inicializa el handler de Loki.
        
        Args:
            url: URL base de Loki (ej: http://localhost:3100)
            labels: Labels adicionales para todos los logs
            buffer_size: Tamaño máximo del buffer antes de flush
            flush_interval: Intervalo en segundos para flush automático
            timeout: Timeout para requests HTTP
        """
        super().__init__()
        self.url = url.rstrip('/')
        self.push_url = f"{self.url}/loki/api/v1/push"
        self.labels = labels or {}
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.timeout = timeout
        self._loki_available = LOKI_ENABLED and _requests_available
        
        # Si Loki no está disponible, no inicializar el buffer
        if not self._loki_available:
            self._buffer = None
            self._flush_event = None
            self._lock = None
            self._base_labels = {}
            self._flush_thread = None
            self._closed = True
            if not LOKI_ENABLED:
                # Silencioso - no mostrar mensaje en producción
                pass
            elif not _requests_available:
                # Solo warning si requests no está disponible
                pass
            return
        
        # Buffer de logs
        self._buffer: queue.Queue = queue.Queue()
        self._flush_event = threading.Event()
        self._lock = threading.Lock()
        
        # Labels base
        self._base_labels = {
            "service": "ats-platform",
            **self.labels
        }
        
        # Iniciar thread de flush periódico
        self._flush_thread = threading.Thread(target=self._periodic_flush, daemon=True)
        self._flush_thread.start()
        
        self._closed = False
    
    def emit(self, record: logging.LogRecord):
        """Emite un log record."""
        if self._closed or not self._loki_available:
            return
        
        try:
            # Construir el mensaje
            log_entry = self._format_log_entry(record)
            
            # Agregar al buffer
            self._buffer.put(log_entry)
            
            # Flush si el buffer está lleno
            if self._buffer.qsize() >= self.buffer_size:
                self._flush()
                
        except Exception:
            self.handleError(record)
    
    def _format_log_entry(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Formatea un log record para Loki."""
        # Timestamp en nanosegundos
        timestamp_ns = int(record.created * 1e9)
        
        # Construir mensaje
        message = self.format(record)
        
        # Labels dinámicas basadas en el log
        labels = {
            **self._base_labels,
            "level": record.levelname.lower(),
            "logger": record.name,
        }
        
        # Agregar trace_id si existe
        if hasattr(record, 'trace_id') and record.trace_id:
            labels['trace_id'] = record.trace_id
        
        # Agregar user_id si existe
        if hasattr(record, 'user_id') and record.user_id:
            labels['user_id'] = record.user_id
        
        return {
            "timestamp": timestamp_ns,
            "labels": labels,
            "message": message
        }
    
    def _flush(self):
        """Envía los logs acumulados a Loki."""
        if not self._loki_available or self._lock is None:
            return
            
        with self._lock:
            if self._buffer is None or self._buffer.empty():
                return
            
            # Extraer logs del buffer
            logs = []
            while not self._buffer.empty() and len(logs) < self.buffer_size:
                try:
                    logs.append(self._buffer.get_nowait())
                except queue.Empty:
                    break
            
            if not logs:
                return
            
            # Si requests no está disponible, descartar logs
            if not _requests_available:
                return
            
            # Agrupar por labels
            streams = {}
            for log in logs:
                labels_key = json.dumps(log['labels'], sort_keys=True)
                if labels_key not in streams:
                    streams[labels_key] = {
                        "stream": log['labels'],
                        "values": []
                    }
                streams[labels_key]["values"].append([
                    str(log['timestamp']),
                    log['message']
                ])
            
            # Construir payload
            payload = {
                "streams": list(streams.values())
            }
            
            # Enviar a Loki
            try:
                response = requests.post(
                    self.push_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout
                )
                response.raise_for_status()
            except Exception as e:
                # Re-encolar logs para reintento (con límite)
                if len(logs) <= self.buffer_size // 2:
                    for log in logs:
                        try:
                            self._buffer.put_nowait(log)
                        except queue.Full:
                            break
                # Loggear error localmente (solo en debug)
                logger.debug(f"[LokiHandler] Error enviando logs: {e}")
    
    def _periodic_flush(self):
        """Thread que hace flush periódico."""
        if not self._loki_available:
            return
            
        while not self._closed:
            self._flush_event.wait(self.flush_interval)
            self._flush_event.clear()
            if not self._closed:
                self._flush()
    
    def flush(self):
        """Fuerza el envío de logs acumulados."""
        if self._loki_available:
            self._flush()
        super().flush()
    
    def close(self):
        """Cierra el handler enviando logs pendientes."""
        self._closed = True
        if self._flush_event:
            self._flush_event.set()
        if self._loki_available:
            self._flush()
        super().close()


class LokiFormatter(logging.Formatter):
    """Formatter que genera logs en formato JSON para Loki."""
    
    def __init__(self, include_extra_fields: bool = True):
        super().__init__()
        self.include_extra_fields = include_extra_fields
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatea el record como JSON."""
        log_obj = {
            "message": record.getMessage(),
            "level": record.levelname,
            "logger": record.name,
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
        }
        
        # Agregar información de excepción si existe
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Agregar campos extra
        if self.include_extra_fields:
            # Campos estándar que pueden venir en extra
            standard_fields = [
                'trace_id', 'span_id', 'user_id', 'request_id',
                'endpoint', 'method', 'status_code', 'duration_ms',
                'entity_type', 'entity_id', 'action'
            ]
            
            for field in standard_fields:
                if hasattr(record, field):
                    log_obj[field] = getattr(record, field)
            
            # Agregar cualquier otro campo extra
            if hasattr(record, 'extras'):
                log_obj.update(record.extras)
        
        return json.dumps(log_obj, ensure_ascii=False)


def setup_loki_logging(
    loki_url: str = "http://localhost:3100",
    service_name: str = "ats-platform",
    environment: str = "development",
    level: int = logging.INFO,
    enable_console: bool = True
):
    """
    Configura logging con Loki.
    
    Si LOKI_ENABLED=false o las librerías no están disponibles,
    configura solo logging a consola/archivo.
    
    Args:
        loki_url: URL de Loki
        service_name: Nombre del servicio
        environment: Ambiente (development, staging, production)
        level: Nivel de logging
        enable_console: Si True, también loggea a consola
    
    Returns:
        LokiHandler o None si está deshabilitado
    """
    # Verificar si Loki está habilitado
    if not LOKI_ENABLED:
        logger.info("Loki logging deshabilitado por configuración (LOKI_ENABLED=false)")
        # Configurar solo consola
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers = []
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        root_logger.addHandler(console_handler)
        return None
    
    if not _requests_available:
        logger.warning("requests no disponible. Configurando solo logging a consola.")
        # Configurar solo consola
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers = []
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        root_logger.addHandler(console_handler)
        return None
    
    try:
        # Configurar root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Limpiar handlers existentes
        root_logger.handlers = []
        
        # Handler de Loki
        loki_handler = LokiHandler(
            url=loki_url,
            labels={
                "service": service_name,
                "environment": environment
            }
        )
        loki_handler.setFormatter(LokiFormatter())
        root_logger.addHandler(loki_handler)
        
        # Handler de consola (opcional)
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            root_logger.addHandler(console_handler)
        
        logger.info(f"Loki logging configurado: {loki_url}")
        return loki_handler
        
    except Exception as e:
        logger.error(f"Error configurando Loki: {e}. Usando consola.")
        # Fallback a consola
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers = []
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        root_logger.addHandler(console_handler)
        return None


# Filter para agregar trace_id automáticamente
class TraceIdFilter(logging.Filter):
    """Filter que agrega trace_id a los logs."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from app.core.tracing import get_trace_id, get_span_id
            
            trace_id = get_trace_id()
            span_id = get_span_id()
            
            if trace_id:
                record.trace_id = trace_id
            if span_id:
                record.span_id = span_id
        except Exception:
            # Si hay error obteniendo trace_id, continuar sin él
            pass
        
        return True
