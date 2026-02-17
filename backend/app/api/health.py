"""Health checks avanzados para monitoreo de producción."""
import psutil
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import httpx

from app.core.config import settings
from app.core.database import get_db
from app.core.alerts import alert_manager, AlertSeverity, AlertStatus
from app.metrics import (
    db_connections_active, db_connections_idle,
    disk_usage_percent, process_memory_usage_percent
)

router = APIRouter()


class HealthStatus:
    """Estados de health check."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


async def check_database(db: AsyncSession) -> Dict[str, Any]:
    """Verifica la conexión a la base de datos."""
    try:
        start = datetime.now()
        result = await db.execute(text("SELECT 1"))
        row = result.fetchone()
        latency_ms = (datetime.now() - start).total_seconds() * 1000
        
        # Intentar obtener información de conexiones activas
        try:
            conn_result = await db.execute(text(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            ))
            conn_row = conn_result.fetchone()
            active_connections = conn_row[0] if conn_row else None
            if active_connections is not None:
                db_connections_active.set(active_connections)
        except:
            active_connections = None
        
        return {
            "status": HealthStatus.HEALTHY,
            "latency_ms": round(latency_ms, 2),
            "active_connections": active_connections
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e)
        }


async def check_redis() -> Dict[str, Any]:
    """Verifica la conexión a Redis."""
    try:
        start = datetime.now()
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=5)
        await r.ping()
        latency_ms = (datetime.now() - start).total_seconds() * 1000
        await r.close()
        
        return {
            "status": HealthStatus.HEALTHY,
            "latency_ms": round(latency_ms, 2)
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e)
        }


async def check_openai() -> Dict[str, Any]:
    """Verifica la conexión a OpenAI."""
    if not settings.OPENAI_API_KEY:
        return {
            "status": HealthStatus.DEGRADED,
            "message": "OPENAI_API_KEY no configurada"
        }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
            )
            
            if response.status_code == 200:
                return {
                    "status": HealthStatus.HEALTHY,
                    "models_available": len(response.json().get("data", []))
                }
            elif response.status_code == 401:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "error": "API key inválida"
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "error": f"Status code: {response.status_code}"
                }
    except Exception as e:
        return {
            "status": HealthStatus.DEGRADED,
            "error": str(e)
        }


def check_disk_space() -> Dict[str, Any]:
    """Verifica el espacio en disco."""
    try:
        disk = psutil.disk_usage('/')
        usage_percent = disk.percent
        
        # Actualizar métrica
        disk_usage_percent.labels(path='/').set(usage_percent)
        
        status = HealthStatus.HEALTHY
        if usage_percent > 90:
            status = HealthStatus.UNHEALTHY
        elif usage_percent > 80:
            status = HealthStatus.DEGRADED
        
        return {
            "status": status,
            "usage_percent": usage_percent,
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2)
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e)
        }


def check_memory() -> Dict[str, Any]:
    """Verifica el uso de memoria."""
    try:
        memory = psutil.virtual_memory()
        usage_percent = memory.percent
        
        # Actualizar métrica
        process_memory_usage_percent.set(usage_percent)
        
        status = HealthStatus.HEALTHY
        if usage_percent > 95:
            status = HealthStatus.UNHEALTHY
        elif usage_percent > 85:
            status = HealthStatus.DEGRADED
        
        return {
            "status": status,
            "usage_percent": usage_percent,
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2)
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e)
        }


def check_cpu() -> Dict[str, Any]:
    """Verifica el uso de CPU."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        
        status = HealthStatus.HEALTHY
        if cpu_percent > 95:
            status = HealthStatus.UNHEALTHY
        elif cpu_percent > 80:
            status = HealthStatus.DEGRADED
        
        return {
            "status": status,
            "usage_percent": cpu_percent,
            "cores": cpu_count
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e)
        }


def get_system_info() -> Dict[str, Any]:
    """Obtiene información del sistema."""
    try:
        process = psutil.Process()
        
        return {
            "python_version": os.sys.version,
            "pid": process.pid,
            "uptime_seconds": int(datetime.now().timestamp() - process.create_time()),
            "threads": process.num_threads(),
            "open_files": len(process.open_files()),
            "connections": len(process.connections())
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check completo del sistema.
    
    Verifica:
    - Base de datos
    - Redis
    - OpenAI API
    - Espacio en disco
    - Memoria
    - CPU
    """
    # Ejecutar todos los checks
    db_status = await check_database(db)
    redis_status = await check_redis()
    openai_status = await check_openai()
    disk_status = check_disk_space()
    memory_status = check_memory()
    cpu_status = check_cpu()
    
    # Determinar estado general
    all_statuses = [
        db_status["status"],
        redis_status["status"],
        openai_status["status"],
        disk_status["status"],
        memory_status["status"],
        cpu_status["status"]
    ]
    
    if HealthStatus.UNHEALTHY in all_statuses:
        overall_status = HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in all_statuses:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY
    
    response = {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {
            "database": db_status,
            "redis": redis_status,
            "openai": openai_status,
            "disk": disk_status,
            "memory": memory_status,
            "cpu": cpu_status
        },
        "system": get_system_info()
    }
    
    # Si está unhealthy, retornar 503
    if overall_status == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail=response)
    
    return response


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe para Kubernetes.
    
    Verifica que la aplicación esté lista para recibir tráfico.
    """
    db_status = await check_database(db)
    redis_status = await check_redis()
    
    if db_status["status"] == HealthStatus.UNHEALTHY or \
       redis_status["status"] == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail={
            "ready": False,
            "database": db_status,
            "redis": redis_status
        })
    
    return {"ready": True}


@router.get("/health/live")
async def liveness_check():
    """
    Liveness probe para Kubernetes.
    
    Verifica que la aplicación esté viva.
    """
    return {"alive": True}


@router.get("/health/alerts")
async def get_alerts():
    """
    Obtiene alertas activas.
    """
    active_alerts = alert_manager.get_active_alerts()
    return {
        "active_alerts": [alert.to_dict() for alert in active_alerts],
        "count": len(active_alerts)
    }


@router.get("/health/metrics")
async def health_metrics():
    """
    Métricas resumidas para health checking.
    """
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}
