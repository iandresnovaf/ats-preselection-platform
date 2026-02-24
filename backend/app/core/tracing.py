"""
Configuración de OpenTelemetry para trazas distribuidas.
Integración con Jaeger para visualización (OPCIONAL).

Este módulo puede funcionar sin Jaeger/Loki configurados.
Set OTEL_ENABLED=false para deshabilitar completamente.
"""
import os
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, Callable

# Logger para este módulo
logger = logging.getLogger(__name__)

# Variable global para tracking de disponibilidad
_otel_available = False
_tracer_provider = None

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.propagate import extract, inject, set_global_textmap
    from opentelemetry.propagators.composite import CompositePropagator
    from opentelemetry.propagators.b3 import B3Format
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    _otel_available = True
except ImportError as e:
    logger.warning(f"OpenTelemetry no disponible: {e}. Tracing deshabilitado.")
    # Crear stubs para que el código no falle
    class _StubTracer:
        def start_as_current_span(self, *args, **kwargs):
            class _StubContext:
                def __enter__(self):
                    return None
                def __exit__(self, *args):
                    pass
            return _StubContext()
    
    class _StubTrace:
        SpanKind = type('SpanKind', (), {'INTERNAL': 0, 'SERVER': 1, 'CLIENT': 2, 'PRODUCER': 3, 'CONSUMER': 4})
        @staticmethod
        def get_tracer(*args, **kwargs):
            return _StubTracer()
        @staticmethod
        def get_current_span():
            return None
        @staticmethod
        def set_tracer_provider(*args, **kwargs):
            pass
    
    class _StubStatus:
        def __init__(self, *args, **kwargs):
            pass
    
    class _StubStatusCode:
        OK = 'OK'
        ERROR = 'ERROR'
    
    trace = _StubTrace()
    Status = _StubStatus
    StatusCode = _StubStatusCode()
    extract = lambda x: None
    inject = lambda x: None
    set_global_textmap = lambda x: None

# Verificar si OTEL está habilitado
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "true").lower() == "true" and _otel_available

# Resource para identificar el servicio (solo si OTEL está disponible)
resource = None
if _otel_available:
    try:
        resource = Resource.create({
            SERVICE_NAME: "ats-platform",
            SERVICE_VERSION: os.getenv("APP_VERSION", "1.0.0"),
            DEPLOYMENT_ENVIRONMENT: os.getenv("ENVIRONMENT", "development"),
            "service.namespace": "ats",
            "host.name": os.getenv("HOSTNAME", "unknown"),
        })
        
        # Configurar propagador global (TraceContext + B3 para compatibilidad)
        propagator = CompositePropagator([
            TraceContextTextMapPropagator(),
            B3Format()
        ])
        set_global_textmap(propagator)
    except Exception as e:
        logger.warning(f"Error configurando recursos OpenTelemetry: {e}")

# Provider global
tracer_provider: Optional[Any] = None


def init_tracer(
    jaeger_endpoint: Optional[str] = None,
    console_export: bool = False,
    sample_rate: float = 1.0
) -> Optional[Any]:
    """
    Inicializa el tracer de OpenTelemetry.
    
    Si OTEL_ENABLED=false o las librerías no están instaladas,
    la función retorna None sin fallar.
    
    Args:
        jaeger_endpoint: URL del collector de Jaeger (ej: http://jaeger:4317)
        console_export: Si True, exporta spans a consola (para debug)
        sample_rate: Tasa de muestreo (0.0 - 1.0)
    
    Returns:
        TracerProvider configurado o None si está deshabilitado
    """
    global tracer_provider
    
    # Verificar si OTEL está habilitado
    if not OTEL_ENABLED:
        logger.info("OpenTelemetry deshabilitado por configuración (OTEL_ENABLED=false)")
        return None
    
    if not _otel_available:
        logger.warning("OpenTelemetry no disponible. Instale: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp")
        return None
    
    try:
        # Crear provider
        provider = TracerProvider(
            resource=resource,
            # Sampler: sampleo probabilístico
            sampler=TraceIdRatioBased(sample_rate)
        )
        
        # Exportador OTLP para Jaeger (solo si hay endpoint)
        if jaeger_endpoint:
            try:
                otlp_exporter = OTLPSpanExporter(
                    endpoint=jaeger_endpoint,
                    insecure=not jaeger_endpoint.startswith("https")
                )
                provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )
                logger.info(f"Jaeger exporter configurado: {jaeger_endpoint}")
            except Exception as e:
                logger.warning(f"No se pudo conectar a Jaeger: {e}. Tracing funcionará sin exportador.")
        
        # Exportador a consola (para debugging)
        if console_export or os.getenv("OTEL_LOG_LEVEL") == "debug":
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
            logger.info("Console exporter habilitado")
        
        # Setear provider global
        trace.set_tracer_provider(provider)
        tracer_provider = provider
        
        logger.info("OpenTelemetry tracer inicializado correctamente")
        return provider
        
    except Exception as e:
        logger.error(f"Error inicializando OpenTelemetry: {e}")
        return None


def get_tracer(name: str = "ats-platform"):
    """Obtiene un tracer para el nombre especificado."""
    if not OTEL_ENABLED or not _otel_available:
        return _StubTracer()
    return trace.get_tracer(name)


class TracingContext:
    """Contexto para manejo de spans."""
    
    def __init__(self, tracer_name: str = "ats-platform"):
        self.tracer = get_tracer(tracer_name)
        self.current_span = None
    
    @contextmanager
    def start_span(
        self,
        name: str,
        kind: Any = None,
        attributes: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        """
        Context manager para crear un span.
        Si OTEL no está disponible, retorna un stub que no hace nada.
        
        Args:
            name: Nombre del span
            kind: Tipo de span
            attributes: Atributos del span
            parent: Span padre (opcional)
        """
        if not OTEL_ENABLED or not _otel_available:
            yield None
            return
            
        try:
            with self.tracer.start_as_current_span(
                name,
                kind=kind or trace.SpanKind.INTERNAL,
                attributes=attributes,
                parent=parent
            ) as span:
                self.current_span = span
                yield span
        except Exception as e:
            logger.debug(f"Error en start_span: {e}")
            yield None
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Agrega un evento al span actual."""
        if self.current_span and OTEL_ENABLED:
            try:
                self.current_span.add_event(name, attributes)
            except Exception as e:
                logger.debug(f"Error en add_event: {e}")
    
    def set_attribute(self, key: str, value: Any):
        """Setea un atributo en el span actual."""
        if self.current_span and OTEL_ENABLED:
            try:
                self.current_span.set_attribute(key, value)
            except Exception as e:
                logger.debug(f"Error en set_attribute: {e}")
    
    def set_status(self, status: Any, description: str = None):
        """Setea el status del span actual."""
        if self.current_span and OTEL_ENABLED:
            try:
                self.current_span.set_status(Status(status, description))
            except Exception as e:
                logger.debug(f"Error en set_status: {e}")
    
    def record_exception(self, exception: Exception):
        """Registra una excepción en el span actual."""
        if self.current_span and OTEL_ENABLED:
            try:
                self.current_span.record_exception(exception)
            except Exception as e:
                logger.debug(f"Error en record_exception: {e}")


def create_tracing_middleware(tracer_name: str = "ats-platform"):
    """
    Crea un middleware de FastAPI para tracing automático.
    Si OTEL no está disponible, retorna un middleware que no hace tracing
    pero sí agrega X-Trace-ID para compatibilidad.
    
    Returns:
        Middleware function
    """
    from fastapi import Request, Response
    import uuid
    
    # Si OTEL no está disponible, retornar middleware simple
    if not OTEL_ENABLED or not _otel_available:
        async def simple_middleware(request: Request, call_next):
            # Generar un trace_id simple para compatibilidad
            trace_id = str(uuid.uuid4())
            response = await call_next(request)
            response.headers["X-Trace-ID"] = trace_id
            return response
        return simple_middleware
    
    tracer = get_tracer(tracer_name)
    
    async def tracing_middleware(request: Request, call_next):
        try:
            # Extraer contexto de traza de los headers
            carrier = {
                key.lower(): value 
                for key, value in request.headers.items()
            }
            context = extract(carrier)
            
            # Crear span para el request
            with tracer.start_as_current_span(
                f"{request.method} {request.url.path}",
                kind=trace.SpanKind.SERVER,
                context=context
            ) as span:
                # Agregar atributos del request
                if span:
                    span.set_attribute("http.method", request.method)
                    span.set_attribute("http.url", str(request.url))
                    span.set_attribute("http.target", str(request.url.path))
                    span.set_attribute("http.host", request.headers.get("host", "unknown"))
                    span.set_attribute("http.user_agent", request.headers.get("user-agent", "unknown"))
                    
                    # Extraer user_id si existe
                    user_id = request.headers.get("X-User-ID")
                    if user_id:
                        span.set_attribute("user.id", user_id)
                
                # Agregar trace_id al response header
                try:
                    current_span = trace.get_current_span()
                    if current_span:
                        trace_id = format(current_span.get_span_context().trace_id, '032x')
                    else:
                        trace_id = str(uuid.uuid4())
                except:
                    trace_id = str(uuid.uuid4())
                
                try:
                    response = await call_next(request)
                    
                    # Agregar atributos del response
                    if span:
                        span.set_attribute("http.status_code", response.status_code)
                        span.set_attribute("http.response_content_length", response.headers.get("content-length", 0))
                        
                        # Setear status basado en código HTTP
                        if response.status_code >= 500:
                            span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                        elif response.status_code >= 400:
                            span.set_status(Status(StatusCode.ERROR, f"Client Error {response.status_code}"))
                        else:
                            span.set_status(Status(StatusCode.OK))
                    
                    # Agregar header X-Trace-ID
                    response.headers["X-Trace-ID"] = trace_id
                    
                    return response
                    
                except Exception as exc:
                    if span:
                        span.set_status(Status(StatusCode.ERROR, str(exc)))
                        span.record_exception(exc)
                    raise
        except Exception as e:
            # Si hay cualquier error en el tracing, continuar sin tracing
            logger.debug(f"Error en tracing middleware: {e}")
            response = await call_next(request)
            response.headers["X-Trace-ID"] = str(uuid.uuid4())
            return response
    
    return tracing_middleware


def instrument_openai(tracer_name: str = "ats-platform.llm"):
    """
    Instrumenta llamadas a OpenAI para tracing.
    Si OTEL no está disponible, retorna la función sin modificar.
    
    Returns:
        Decorador para funciones que llaman a OpenAI
    """
    def decorator(func: Callable) -> Callable:
        # Si OTEL no está disponible, retornar función sin modificar
        if not OTEL_ENABLED or not _otel_available:
            return func
            
        import functools
        tracer = get_tracer(tracer_name)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            operation = func.__name__
            model = kwargs.get('model', 'unknown')
            
            try:
                with tracer.start_as_current_span(
                    f"openai.{operation}",
                    kind=trace.SpanKind.CLIENT,
                    attributes={
                        "llm.provider": "openai",
                        "llm.model": model,
                        "llm.operation": operation,
                    }
                ) as span:
                    try:
                        # Capturar tokens si están disponibles
                        prompt_tokens = kwargs.get('prompt_tokens', 0)
                        if prompt_tokens and span:
                            span.set_attribute("llm.prompt_tokens", prompt_tokens)
                        
                        result = await func(*args, **kwargs)
                        
                        # Agregar atributos de respuesta
                        if span and hasattr(result, 'usage'):
                            span.set_attribute("llm.completion_tokens", result.usage.completion_tokens)
                            span.set_attribute("llm.total_tokens", result.usage.total_tokens)
                        
                        if span:
                            span.set_status(Status(StatusCode.OK))
                        
                        return result
                        
                    except Exception as exc:
                        if span:
                            span.set_status(Status(StatusCode.ERROR, str(exc)))
                            span.record_exception(exc)
                        raise
            except Exception:
                # Si hay error en tracing, ejecutar función normalmente
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            operation = func.__name__
            model = kwargs.get('model', 'unknown')
            
            try:
                with tracer.start_as_current_span(
                    f"openai.{operation}",
                    kind=trace.SpanKind.CLIENT,
                    attributes={
                        "llm.provider": "openai",
                        "llm.model": model,
                        "llm.operation": operation,
                    }
                ) as span:
                    try:
                        result = func(*args, **kwargs)
                        if span:
                            span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as exc:
                        if span:
                            span.set_status(Status(StatusCode.ERROR, str(exc)))
                            span.record_exception(exc)
                        raise
            except Exception:
                return func(*args, **kwargs)
        
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def instrument_celery_task(tracer_name: str = "ats-platform.worker"):
    """
    Instrumenta tareas de Celery para tracing.
    Si OTEL no está disponible, retorna la función sin modificar.
    
    Uso:
        @app.task
        @instrument_celery_task()
        def my_task():
            pass
    """
    def decorator(task_func: Callable) -> Callable:
        # Si OTEL no está disponible, retornar función sin modificar
        if not OTEL_ENABLED or not _otel_available:
            return task_func
            
        import functools
        tracer = get_tracer(tracer_name)
        
        @functools.wraps(task_func)
        def wrapper(*args, **kwargs):
            task_name = task_func.__name__
            
            try:
                # Extraer trace context de kwargs si existe
                trace_context = kwargs.pop('trace_context', None)
                context = extract(trace_context) if trace_context else None
                
                with tracer.start_as_current_span(
                    f"celery.{task_name}",
                    kind=trace.SpanKind.CONSUMER,
                    context=context,
                    attributes={
                        "messaging.system": "celery",
                        "messaging.destination": task_name,
                        "messaging.destination_kind": "queue",
                    }
                ) as span:
                    # Agregar argumentos como atributos (sanitizados)
                    if span:
                        span.set_attribute("celery.task_name", task_name)
                        span.set_attribute("celery.args_count", len(args))
                    
                    try:
                        result = task_func(*args, **kwargs)
                        if span:
                            span.set_status(Status(StatusCode.OK))
                            span.set_attribute("celery.status", "success")
                        return result
                        
                    except Exception as exc:
                        if span:
                            span.set_status(Status(StatusCode.ERROR, str(exc)))
                            span.record_exception(exc)
                            span.set_attribute("celery.status", "failure")
                            span.set_attribute("celery.error_type", type(exc).__name__)
                        raise
            except Exception:
                # Si hay error en tracing, ejecutar función normalmente
                return task_func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def get_trace_id() -> Optional[str]:
    """Obtiene el trace_id actual como string hexadecimal."""
    if not OTEL_ENABLED or not _otel_available:
        return None
    try:
        current_span = trace.get_current_span()
        if current_span:
            span_context = current_span.get_span_context()
            if span_context.is_valid:
                return format(span_context.trace_id, '032x')
    except Exception:
        pass
    return None


def get_span_id() -> Optional[str]:
    """Obtiene el span_id actual como string hexadecimal."""
    if not OTEL_ENABLED or not _otel_available:
        return None
    try:
        current_span = trace.get_current_span()
        if current_span:
            span_context = current_span.get_span_context()
            if span_context.is_valid:
                return format(span_context.span_id, '016x')
    except Exception:
        pass
    return None


def inject_trace_context(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Inyecta el contexto de traza en headers HTTP.
    
    Args:
        headers: Dict de headers existente
    
    Returns:
        Headers con contexto de traza inyectado (o sin cambios si OTEL está deshabilitado)
    """
    if not OTEL_ENABLED or not _otel_available:
        return headers
    try:
        inject(headers)
    except Exception as e:
        logger.debug(f"Error inyectando trace context: {e}")
    return headers
