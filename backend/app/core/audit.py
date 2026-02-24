"""
Sistema de Auditoría de Base de Datos para ATS Platform.

Usa SQLAlchemy events para registrar automáticamente cambios en tablas críticas.
Los logs se almacenan en la tabla hh_audit_log.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.logging import get_logger

logger = get_logger(__name__)

# Tablas que serán auditadas (nombres de clase)
AUDITED_TABLES = {
    'HHCandidate',
    'HHClient',
    'HHRole',
    'HHApplication',
    'HHDocument',
    'HHInterview',
    'HHAssessment',
    'User',
}

# Campos sensibles que deben ofuscarse en los logs
SENSITIVE_FIELDS = {
    'password', 'password_hash', 'secret', 'token', 
    'email', 'phone', 'national_id', 'cv_text', 'raw_text'
}


def get_entity_diff(instance, action: str) -> Dict[str, Any]:
    """
    Obtiene la diferencia entre el estado actual y el anterior de una entidad.
    
    Args:
        instance: Instancia del modelo
        action: Tipo de acción (create, update, delete)
    
    Returns:
        Diccionario con los cambios
    """
    diff = {
        'action': action,
        'entity_type': instance.__class__.__name__,
        'entity_id': str(getattr(instance, 'id', getattr(instance, 'candidate_id', 
                   getattr(instance, 'client_id', getattr(instance, 'role_id',
                   getattr(instance, 'application_id', getattr(instance, 'user_id', 'unknown'))))))),
        'timestamp': datetime.utcnow().isoformat(),
        'changes': {}
    }
    
    if action == 'create':
        # Para creación, registrar todos los campos no nulos
        for key, value in instance.__dict__.items():
            if key.startswith('_'):
                continue
            if value is not None:
                diff['changes'][key] = {
                    'old': None,
                    'new': _serialize_value(value, key)
                }
    
    elif action == 'update':
        # Para actualización, registrar solo los campos modificados
        inspector = inspect(instance)
        
        for attr in inspector.attrs:
            key = attr.key
            history = attr.history
            
            if history.has_changes():
                old_value = history.deleted[0] if history.deleted else None
                new_value = history.added[0] if history.added else None
                
                diff['changes'][key] = {
                    'old': _serialize_value(old_value, key),
                    'new': _serialize_value(new_value, key)
                }
    
    elif action == 'delete':
        # Para eliminación, registrar todos los campos
        for key, value in instance.__dict__.items():
            if key.startswith('_'):
                continue
            diff['changes'][key] = {
                'old': _serialize_value(value, key),
                'new': None
            }
    
    return diff


def _serialize_value(value: Any, field_name: str) -> Any:
    """
    Serializa un valor para almacenar en el log.
    Ofusca campos sensibles.
    """
    # Ofuscar campos sensibles
    if field_name.lower() in SENSITIVE_FIELDS:
        if value is None:
            return None
        str_value = str(value)
        if len(str_value) <= 4:
            return '*' * len(str_value)
        return str_value[:2] + '*' * (len(str_value) - 4) + str_value[-2:]
    
    # Serializar UUIDs
    if isinstance(value, UUID):
        return str(value)
    
    # Serializar datetimes
    if isinstance(value, datetime):
        return value.isoformat()
    
    # Serializar listas y diccionarios
    if isinstance(value, (list, dict)):
        try:
            return json.loads(json.dumps(value, default=str))
        except:
            return str(value)[:1000]  # Limitar tamaño
    
    # Otros tipos
    return value


def _should_audit(instance) -> bool:
    """Determina si una entidad debe ser auditada."""
    return instance.__class__.__name__ in AUDITED_TABLES


def _get_current_user_id() -> Optional[str]:
    """
    Obtiene el ID del usuario actual del contexto.
    Esta función debe ser implementada según el sistema de autenticación.
    """
    # TODO: Integrar con sistema de autenticación
    # Por ahora retorna None, pero puede obtenerse del contexto de la request
    try:
        from starlette_context import context
        return context.get('user_id')
    except:
        return None


async def save_audit_log(db: Session, diff: Dict[str, Any]) -> None:
    """
    Guarda el log de auditoría en la base de datos.
    Usa inserción directa SQL para evitar recursividad.
    """
    try:
        # Importar aquí para evitar import circular
        from sqlalchemy import text
        
        query = text("""
            INSERT INTO hh_audit_log (entity_type, entity_id, action, changed_by, diff_json)
            VALUES (:entity_type, :entity_id, :action, :changed_by, :diff_json)
        """)
        
        await db.execute(query, {
            'entity_type': diff['entity_type'],
            'entity_id': diff['entity_id'],
            'action': diff['action'],
            'changed_by': _get_current_user_id(),
            'diff_json': json.dumps(diff['changes'])
        })
    except Exception as e:
        # Loggear error pero no fallar la operación principal
        logger.error(f"Error guardando audit log: {e}")


def setup_audit_events():
    """
    Configura los event listeners de SQLAlchemy para auditoría.
    Debe llamarse después de definir todos los modelos.
    """
    from app.models.core_ats import HHAuditLog
    
    @event.listens_for(Session, 'after_flush')
    def after_flush(session, flush_context):
        """Evento después de hacer flush - captura cambios pendientes."""
        # No auditamos operaciones sobre la tabla de auditoría misma
        if hasattr(session, '_audit_logs'):
            return
        
        session._audit_logs = []
        
        for instance in session.new:
            if _should_audit(instance):
                diff = get_entity_diff(instance, 'create')
                session._audit_logs.append(diff)
        
        for instance in session.dirty:
            if _should_audit(instance):
                diff = get_entity_diff(instance, 'update')
                session._audit_logs.append(diff)
        
        for instance in session.deleted:
            if _should_audit(instance):
                diff = get_entity_diff(instance, 'delete')
                session._audit_logs.append(diff)
    
    @event.listens_for(Session, 'after_commit')
    def after_commit(session):
        """Evento después de commit - loggear cambios confirmados."""
        if not hasattr(session, '_audit_logs'):
            return
        
        for diff in session._audit_logs:
            logger.info(
                f"AUDIT: {diff['action']} on {diff['entity_type']} (id={diff['entity_id']})",
                extra={
                    'audit_action': diff['action'],
                    'entity_type': diff['entity_type'],
                    'entity_id': diff['entity_id'],
                    'changes': diff['changes']
                }
            )
        
        # Limpiar logs procesados
        delattr(session, '_audit_logs')
    
    @event.listens_for(Session, 'after_rollback')
    def after_rollback(session):
        """Limpiar logs pendientes en caso de rollback."""
        if hasattr(session, '_audit_logs'):
            delattr(session, '_audit_logs')
    
    logger.info("Sistema de auditoría de base de datos inicializado")


def get_audit_logs(
    db: Session,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Consulta logs de auditoría con filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        entity_type: Filtrar por tipo de entidad
        entity_id: Filtrar por ID de entidad
        action: Filtrar por tipo de acción (create, update, delete)
        limit: Límite de resultados
        offset: Offset para paginación
    
    Returns:
        Lista de logs de auditoría
    """
    from sqlalchemy import text
    
    where_clauses = []
    params = {'limit': limit, 'offset': offset}
    
    if entity_type:
        where_clauses.append("entity_type = :entity_type")
        params['entity_type'] = entity_type
    
    if entity_id:
        where_clauses.append("entity_id = :entity_id")
        params['entity_id'] = entity_id
    
    if action:
        where_clauses.append("action = :action")
        params['action'] = action
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    query = text(f"""
        SELECT audit_id, entity_type, entity_id, action, changed_by, changed_at, diff_json
        FROM hh_audit_log
        WHERE {where_sql}
        ORDER BY changed_at DESC
        LIMIT :limit OFFSET :offset
    """)
    
    result = db.execute(query, params)
    
    logs = []
    for row in result:
        logs.append({
            'audit_id': str(row.audit_id),
            'entity_type': row.entity_type,
            'entity_id': str(row.entity_id),
            'action': row.action,
            'changed_by': row.changed_by,
            'changed_at': row.changed_at.isoformat() if row.changed_at else None,
            'diff': json.loads(row.diff_json) if row.diff_json else {}
        })
    
    return logs
