"""
Servicio de Auditoría para el ATS Platform.
Gestiona el registro de auditoría en la base de datos (HHAuditLog).
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from app.models.core_ats import HHAuditLog, AuditAction

logger = logging.getLogger(__name__)


class AuditService:
    """Servicio para gestionar auditoría de operaciones."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_event(
        self,
        entity_type: str,
        entity_id: UUID,
        action: AuditAction,
        changed_by: Optional[str] = None,
        diff_json: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> HHAuditLog:
        """
        Registra un evento de auditoría.
        
        Args:
            entity_type: Tipo de entidad (candidate, application, user, role, etc.)
            entity_id: ID de la entidad
            action: Acción realizada (create, update, delete)
            changed_by: ID del usuario que realizó el cambio
            diff_json: Diferencias en formato JSON
            request: Request HTTP para extraer metadatos
            ip_address: IP del cliente (opcional)
            user_agent: User agent del cliente (opcional)
        
        Returns:
            HHAuditLog creado
        """
        # Extraer información del request si está disponible
        client_info = {}
        if request:
            forwarded = request.headers.get("X-Forwarded-For")
            real_ip = request.headers.get("X-Real-IP")
            
            if forwarded:
                client_info['ip'] = forwarded.split(",")[0].strip()
            elif real_ip:
                client_info['ip'] = real_ip
            else:
                client_info['ip'] = request.client.host if request.client else "unknown"
            
            client_info['user_agent'] = request.headers.get("user-agent", "unknown")
            client_info['method'] = request.method
            client_info['path'] = str(request.url.path)
        else:
            client_info['ip'] = ip_address or "unknown"
            client_info['user_agent'] = user_agent or "unknown"
        
        # Agregar metadatos al diff
        full_diff = {
            **(diff_json or {}),
            "_metadata": {
                "ip_address": client_info['ip'],
                "user_agent": client_info['user_agent'],
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        audit_log = HHAuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            changed_by=changed_by,
            diff_json=full_diff
        )
        
        self.db.add(audit_log)
        await self.db.flush()
        await self.db.refresh(audit_log)
        
        logger.debug(f"Audit log created: {entity_type} {action} by {changed_by}")
        
        return audit_log
    
    async def log_create(
        self,
        entity_type: str,
        entity_id: UUID,
        data: Dict[str, Any],
        changed_by: Optional[str] = None,
        request: Optional[Request] = None
    ) -> HHAuditLog:
        """Registra una creación de entidad."""
        return await self.log_event(
            entity_type=entity_type,
            entity_id=entity_id,
            action=AuditAction.CREATE,
            changed_by=changed_by,
            diff_json={"new_data": self._sanitize_sensitive_data(entity_type, data)},
            request=request
        )
    
    async def log_update(
        self,
        entity_type: str,
        entity_id: UUID,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        changed_by: Optional[str] = None,
        request: Optional[Request] = None
    ) -> HHAuditLog:
        """Registra una actualización de entidad."""
        diff = self._compute_diff(old_data, new_data)
        
        return await self.log_event(
            entity_type=entity_type,
            entity_id=entity_id,
            action=AuditAction.UPDATE,
            changed_by=changed_by,
            diff_json={
                "changes": self._sanitize_sensitive_data(entity_type, diff),
                "old_values": self._sanitize_sensitive_data(entity_type, {k: old_data.get(k) for k in diff.keys()}),
                "new_values": self._sanitize_sensitive_data(entity_type, {k: new_data.get(k) for k in diff.keys()})
            },
            request=request
        )
    
    async def log_delete(
        self,
        entity_type: str,
        entity_id: UUID,
        old_data: Dict[str, Any],
        changed_by: Optional[str] = None,
        request: Optional[Request] = None
    ) -> HHAuditLog:
        """Registra una eliminación de entidad."""
        return await self.log_event(
            entity_type=entity_type,
            entity_id=entity_id,
            action=AuditAction.DELETE,
            changed_by=changed_by,
            diff_json={"deleted_data": self._sanitize_sensitive_data(entity_type, old_data)},
            request=request
        )
    
    async def log_permission_change(
        self,
        target_user_id: UUID,
        old_role: str,
        new_role: str,
        changed_by: str,
        request: Optional[Request] = None,
        reason: Optional[str] = None
    ) -> HHAuditLog:
        """
        Registra un cambio de permisos/rol de usuario.
        
        Args:
            target_user_id: ID del usuario afectado
            old_role: Rol anterior
            new_role: Nuevo rol
            changed_by: ID del administrador que hizo el cambio
            request: Request HTTP
            reason: Razón del cambio
        """
        diff = {
            "user_id": str(target_user_id),
            "old_role": old_role,
            "new_role": new_role,
            "reason": reason,
            "change_type": "role_modification"
        }
        
        audit_log = await self.log_event(
            entity_type="user_permission",
            entity_id=target_user_id,
            action=AuditAction.UPDATE,
            changed_by=changed_by,
            diff_json=diff,
            request=request
        )
        
        logger.info(f"Permission change logged: User {target_user_id} from {old_role} to {new_role} by {changed_by}")
        
        return audit_log
    
    async def log_data_export(
        self,
        resource_type: str,
        resource_count: int,
        exported_by: str,
        export_format: str,
        request: Optional[Request] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> HHAuditLog:
        """
        Registra una exportación de datos.
        
        Args:
            resource_type: Tipo de recurso exportado (candidates, applications, etc.)
            resource_count: Cantidad de registros exportados
            exported_by: ID del usuario que exportó
            export_format: Formato (csv, json, xlsx, etc.)
            request: Request HTTP
            filters: Filtros aplicados en la exportación
        """
        # Generar ID único para la exportación
        from uuid import uuid4
        export_id = uuid4()
        
        diff = {
            "export_id": str(export_id),
            "resource_type": resource_type,
            "resource_count": resource_count,
            "export_format": export_format,
            "filters": filters or {},
            "exported_at": datetime.utcnow().isoformat()
        }
        
        audit_log = await self.log_event(
            entity_type="data_export",
            entity_id=export_id,
            action=AuditAction.CREATE,
            changed_by=exported_by,
            diff_json=diff,
            request=request
        )
        
        logger.info(f"Data export logged: {resource_count} {resource_type} exported by {exported_by}")
        
        return audit_log
    
    async def log_pii_access(
        self,
        resource_type: str,
        resource_id: UUID,
        action: str,
        accessed_by: str,
        request: Optional[Request] = None,
        fields_accessed: Optional[List[str]] = None
    ) -> HHAuditLog:
        """
        Registra acceso a datos sensibles (PII).
        
        Args:
            resource_type: Tipo de recurso (candidate, user, etc.)
            resource_id: ID del recurso
            action: Acción realizada (view, edit, export, etc.)
            accessed_by: ID del usuario que accedió
            request: Request HTTP
            fields_accessed: Lista de campos sensibles accedidos
        """
        pii_fields = fields_accessed or []
        
        # Lista de campos considerados PII
        sensitive_fields = [
            'email', 'phone', 'national_id', 'full_name', 'address',
            'document', 'salary', 'bank_account', 'date_of_birth'
        ]
        
        # Solo loggear si hay campos PII
        has_pii = any(field in sensitive_fields for field in pii_fields)
        if not has_pii and not fields_accessed:
            return None
        
        diff = {
            "resource_type": resource_type,
            "resource_id": str(resource_id),
            "action": action,
            "fields_accessed": pii_fields,
            "has_pii": True
        }
        
        audit_log = await self.log_event(
            entity_type="pii_access",
            entity_id=resource_id,
            action=AuditAction.CREATE,
            changed_by=accessed_by,
            diff_json=diff,
            request=request
        )
        
        logger.warning(f"PII access logged: {accessed_by} accessed {resource_type} {resource_id}")
        
        return audit_log
    
    async def query_audit_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        action: Optional[AuditAction] = None,
        changed_by: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[HHAuditLog]:
        """
        Consulta logs de auditoría con filtros.
        
        Returns:
            Lista de HHAuditLog
        """
        query = select(HHAuditLog).order_by(desc(HHAuditLog.changed_at))
        
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
            query = query.where(and_(*filters))
        
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: UUID,
        limit: int = 50
    ) -> List[HHAuditLog]:
        """
        Obtiene el historial completo de una entidad.
        
        Args:
            entity_type: Tipo de entidad
            entity_id: ID de la entidad
            limit: Límite de registros
        
        Returns:
            Lista de cambios ordenados por fecha descendente
        """
        return await self.query_audit_logs(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit
        )
    
    def _compute_diff(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Computa las diferencias entre dos diccionarios."""
        diff = {}
        
        all_keys = set(old_data.keys()) | set(new_data.keys())
        
        for key in all_keys:
            old_val = old_data.get(key)
            new_val = new_data.get(key)
            
            if old_val != new_val:
                diff[key] = {"old": old_val, "new": new_val}
        
        return diff
    
    def _sanitize_sensitive_data(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitiza datos sensibles antes de guardar en auditoría.
        Mascara campos sensibles como contraseñas, tokens, etc.
        """
        sensitive_keys = [
            'password', 'hashed_password', 'token', 'access_token', 'refresh_token',
            'secret', 'api_key', 'credit_card', 'ssn', 'social_security'
        ]
        
        sanitized = {}
        for key, value in data.items():
            if any(sk in key.lower() for sk in sensitive_keys):
                sanitized[key] = "***MASKED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_sensitive_data(entity_type, value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_sensitive_data(entity_type, item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized


# Instancia global para uso en middlewares
_audit_service: Optional[AuditService] = None

def get_audit_service(db: AsyncSession) -> AuditService:
    """Obtiene instancia del servicio de auditoría."""
    return AuditService(db)
