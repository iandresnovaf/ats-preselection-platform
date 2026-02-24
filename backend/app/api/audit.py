"""
API endpoints para consulta de auditoría (solo administradores).
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.core_ats import AuditAction, HHAuditLog
from app.services.audit_service import AuditService
from pydantic import BaseModel

router = APIRouter(prefix="/audit", tags=["Audit"])


# =============================================================================
# Schemas
# =============================================================================

class AuditLogResponse(BaseModel):
    """Respuesta de log de auditoría."""
    audit_id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    changed_by: Optional[str]
    changed_at: datetime
    diff_json: Optional[dict]
    
    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Respuesta paginada de logs de auditoría."""
    total: int
    items: List[AuditLogResponse]
    page: int
    page_size: int


class EntityHistoryResponse(BaseModel):
    """Historial de cambios de una entidad."""
    entity_type: str
    entity_id: UUID
    changes: List[AuditLogResponse]


class AuditStatsResponse(BaseModel):
    """Estadísticas de auditoría."""
    total_events_24h: int
    total_events_7d: int
    total_events_30d: int
    events_by_type: dict
    events_by_user: dict
    top_modified_entities: List[dict]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/logs", response_model=AuditLogListResponse)
async def query_audit_logs(
    request: Request,
    entity_type: Optional[str] = Query(None, description="Filtrar por tipo de entidad"),
    entity_id: Optional[UUID] = Query(None, description="Filtrar por ID de entidad"),
    action: Optional[AuditAction] = Query(None, description="Filtrar por acción"),
    changed_by: Optional[str] = Query(None, description="Filtrar por usuario"),
    start_date: Optional[datetime] = Query(None, description="Fecha inicial"),
    end_date: Optional[datetime] = Query(None, description="Fecha final"),
    days: int = Query(0, description="Filtrar últimos N días (sobreescribe fechas)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """
    Consultar logs de auditoría (solo administradores).
    
    Permite filtrar por tipo de entidad, acción, usuario, rango de fechas, etc.
    """
    audit_service = AuditService(db)
    
    # Calcular fechas si se especifica días
    if days > 0:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
    
    # Consultar logs
    logs = await audit_service.query_audit_logs(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changed_by=changed_by,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    
    # Contar total (para paginación)
    from sqlalchemy import select, func, and_
    count_query = select(func.count()).select_from(HHAuditLog)
    
    filters = []
    if entity_type:
        filters.append(HHAuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(HHAuditLog.entity_id == entity_id)
    if action:
        filters.append(HHAuditLog.action == action)
    if changed_by:
        filters.append(HHAuditLog.changed_by == changed_by)
    if start_date:
        filters.append(HHAuditLog.changed_at >= start_date)
    if end_date:
        filters.append(HHAuditLog.changed_at <= end_date)
    
    if filters:
        count_query = count_query.where(and_(*filters))
    
    result = await db.execute(count_query)
    total = result.scalar()
    
    return {
        "total": total,
        "items": logs,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit
    }


@router.get("/logs/{audit_id}", response_model=AuditLogResponse)
async def get_audit_log_detail(
    audit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """
    Obtener detalle de un log de auditoría específico.
    """
    from sqlalchemy import select
    
    result = await db.execute(
        select(HHAuditLog).where(HHAuditLog.audit_id == audit_id)
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Log de auditoría no encontrado")
    
    return log


@router.get("/entity/{entity_type}/{entity_id}/history", response_model=EntityHistoryResponse)
async def get_entity_audit_history(
    entity_type: str,
    entity_id: UUID,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """
    Obtener historial completo de cambios de una entidad específica.
    
    Útil para ver toda la trazabilidad de un candidato, aplicación, etc.
    """
    audit_service = AuditService(db)
    
    history = await audit_service.get_entity_history(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit
    )
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "changes": history
    }


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """
    Obtener estadísticas de auditoría.
    
    Métricas sobre eventos de auditoría en diferentes períodos.
    """
    from sqlalchemy import select, func, and_
    
    now = datetime.utcnow()
    
    # Eventos en últimas 24 horas
    result_24h = await db.execute(
        select(func.count())
        .select_from(HHAuditLog)
        .where(HHAuditLog.changed_at >= now - timedelta(hours=24))
    )
    total_24h = result_24h.scalar()
    
    # Eventos en últimos 7 días
    result_7d = await db.execute(
        select(func.count())
        .select_from(HHAuditLog)
        .where(HHAuditLog.changed_at >= now - timedelta(days=7))
    )
    total_7d = result_7d.scalar()
    
    # Eventos en últimos 30 días
    result_30d = await db.execute(
        select(func.count())
        .select_from(HHAuditLog)
        .where(HHAuditLog.changed_at >= now - timedelta(days=30))
    )
    total_30d = result_30d.scalar()
    
    # Eventos por tipo (últimos 30 días)
    result_by_type = await db.execute(
        select(HHAuditLog.entity_type, func.count())
        .where(HHAuditLog.changed_at >= now - timedelta(days=30))
        .group_by(HHAuditLog.entity_type)
    )
    events_by_type = {row[0]: row[1] for row in result_by_type.all()}
    
    # Eventos por usuario (últimos 30 días)
    result_by_user = await db.execute(
        select(HHAuditLog.changed_by, func.count())
        .where(
            and_(
                HHAuditLog.changed_at >= now - timedelta(days=30),
                HHAuditLog.changed_by.isnot(None)
            )
        )
        .group_by(HHAuditLog.changed_by)
        .order_by(func.count().desc())
        .limit(10)
    )
    events_by_user = {str(row[0]): row[1] for row in result_by_user.all()}
    
    # Entidades más modificadas
    result_top = await db.execute(
        select(
            HHAuditLog.entity_type,
            HHAuditLog.entity_id,
            func.count()
        )
        .where(HHAuditLog.changed_at >= now - timedelta(days=30))
        .group_by(HHAuditLog.entity_type, HHAuditLog.entity_id)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_modified = [
        {
            "entity_type": row[0],
            "entity_id": str(row[1]),
            "change_count": row[2]
        }
        for row in result_top.all()
    ]
    
    return {
        "total_events_24h": total_24h,
        "total_events_7d": total_7d,
        "total_events_30d": total_30d,
        "events_by_type": events_by_type,
        "events_by_user": events_by_user,
        "top_modified_entities": top_modified
    }


@router.get("/security/events")
async def get_security_events(
    event_type: Optional[str] = Query(None, description="Tipo de evento: login, permission_change, export, pii_access"),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """
    Obtener eventos de seguridad específicos.
    
    Eventos: login attempts, permission changes, exports, pii access
    """
    audit_service = AuditService(db)
    
    # Mapear tipos de eventos a tipos de entidad
    entity_type_map = {
        'login': 'user_session',
        'permission_change': 'user_permission',
        'export': 'data_export',
        'pii_access': 'pii_access'
    }
    
    entity_type = entity_type_map.get(event_type)
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    logs = await audit_service.query_audit_logs(
        entity_type=entity_type,
        start_date=start_date,
        limit=500
    )
    
    return {
        "event_type": event_type or "all",
        "days": days,
        "count": len(logs),
        "events": logs
    }
