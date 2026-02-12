"""Servicio de gestión de usuarios."""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.models import User, UserRole, UserStatus
from app.schemas import UserCreate, UserUpdate
from app.core.auth import get_password_hash, verify_password
from app.core.security_logging import SecurityLogger
import secrets
import string

logger = logging.getLogger(__name__)


class UserService:
    """Servicio para gestionar usuarios."""
    
    def __init__(self, db: AsyncSession, request: Optional[Request] = None):
        self.db = db
        self.request = request
        self.security_logger = SecurityLogger()
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Obtener usuario por ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Obtener usuario por email."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    async def list_users(
        self,
        role: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """Listar usuarios con filtros."""
        query = select(User)
        
        # Aplicar filtros
        filters = []
        if role:
            filters.append(User.role == role)
        if status:
            filters.append(User.status == status)
        if search:
            search_filter = or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
            )
            filters.append(search_filter)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Ordenar por fecha de creación descendente
        query = query.order_by(User.created_at.desc())
        
        # Paginación
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_user(self, data: UserCreate, performed_by: Optional[str] = None) -> User:
        """Crear nuevo usuario."""
        logger.info(f"Creando usuario con email: {data.email}")
        
        # Verificar email único
        existing = await self.get_by_email(data.email)
        if existing:
            logger.warning(f"Intento de crear usuario con email duplicado: {data.email}")
            raise ValueError("Ya existe un usuario con este email")
        
        # Generar password temporal si no se proporciona
        password = data.password
        if not password:
            password = self._generate_temp_password()
            # TODO: Enviar email con password temporal
        
        # Crear usuario
        user = User(
            email=data.email.lower(),
            hashed_password=get_password_hash(password),
            full_name=data.full_name,
            phone=data.phone,
            role=UserRole(data.role),
            status=UserStatus.ACTIVE,
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        
        logger.info(f"Usuario creado exitosamente: {user.id}")
        
        # Loggear creación de usuario
        if self.request and performed_by:
            await self.security_logger.log_user_modification(
                self.request,
                action="create",
                target_user_id=str(user.id),
                performed_by=performed_by,
                details={"email": user.email, "role": data.role}
            )
        
        return user
    
    async def update_user(
        self, 
        user_id: str, 
        data: UserUpdate, 
        performed_by: Optional[str] = None
    ) -> Optional[User]:
        """Actualizar usuario."""
        logger.info(f"Actualizando usuario {user_id} - Datos recibidos: {data.model_dump()}")
        
        user = await self.get_by_id(user_id)
        if not user:
            logger.warning(f"Usuario no encontrado: {user_id}")
            return None
        
        # Guardar cambios para logging
        changes = {}
        
        # Verificar email único si se cambia
        if data.email and data.email.lower() != user.email:
            existing = await self.get_by_email(data.email)
            if existing:
                logger.warning(f"Intento de actualizar a email duplicado: {data.email}")
                raise ValueError("Ya existe un usuario con este email")
            changes['email'] = {"old": user.email, "new": data.email.lower()}
            user.email = data.email.lower()
        
        # Actualizar campos
        if data.full_name and data.full_name != user.full_name:
            changes['full_name'] = {"old": user.full_name, "new": data.full_name}
            user.full_name = data.full_name
        if data.phone and data.phone != user.phone:
            changes['phone'] = {"old": "***", "new": "***"}  # Mask phone
            user.phone = data.phone
        
        # Manejar actualización de role con correcta serialización de enum
        if data.role:
            current_role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
            if data.role != current_role_value:
                changes['role'] = {"old": current_role_value, "new": data.role}
                try:
                    user.role = UserRole(data.role)
                    logger.info(f"Role actualizado: {current_role_value} -> {data.role}")
                except ValueError as e:
                    logger.error(f"Error al actualizar role: {e}")
                    raise ValueError(f"Rol no válido: {data.role}")
        
        # Manejar actualización de status con correcta serialización de enum - FIX BUG-001/002
        if data.status:
            current_status_value = user.status.value if hasattr(user.status, 'value') else str(user.status)
            if data.status != current_status_value:
                changes['status'] = {"old": current_status_value, "new": data.status}
                try:
                    user.status = UserStatus(data.status)
                    logger.info(f"Status actualizado: {current_status_value} -> {data.status}")
                except ValueError as e:
                    logger.error(f"Error al actualizar status: {e}")
                    raise ValueError(f"Estado no válido: {data.status}")
        
        user.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(user)
        
        logger.info(f"Usuario {user_id} actualizado exitosamente. Cambios: {changes}")
        
        # Loggear modificación
        if self.request and performed_by and changes:
            await self.security_logger.log_user_modification(
                self.request,
                action="update",
                target_user_id=user_id,
                performed_by=performed_by,
                details=changes
            )
        
        return user
    
    async def update_password(self, user_id: str, new_password: str, performed_by: Optional[str] = None) -> bool:
        """Actualizar password de usuario."""
        logger.info(f"Actualizando password para usuario: {user_id}")
        
        user = await self.get_by_id(user_id)
        if not user:
            logger.warning(f"Usuario no encontrado para cambio de password: {user_id}")
            return False
        
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        await self.db.flush()
        
        logger.info(f"Password actualizado exitosamente para usuario: {user_id}")
        
        # Loggear cambio de contraseña por admin
        if self.request and performed_by and performed_by != user_id:
            await self.security_logger.log_user_modification(
                self.request,
                action="password_reset_by_admin",
                target_user_id=user_id,
                performed_by=performed_by
            )
        
        return True
    
    async def deactivate_user(self, user_id: str, performed_by: Optional[str] = None) -> Optional[User]:
        """Desactivar usuario (soft delete)."""
        logger.info(f"Desactivando usuario: {user_id}")
        
        result = await self.update_user(
            user_id,
            UserUpdate(status=UserStatus.INACTIVE.value),
            performed_by=performed_by
        )
        
        if result:
            logger.info(f"Usuario {user_id} desactivado exitosamente")
        else:
            logger.warning(f"No se pudo desactivar usuario {user_id}")
        
        return result
    
    async def activate_user(self, user_id: str, performed_by: Optional[str] = None) -> Optional[User]:
        """Activar usuario."""
        logger.info(f"Activando usuario: {user_id}")
        
        result = await self.update_user(
            user_id,
            UserUpdate(status=UserStatus.ACTIVE.value),
            performed_by=performed_by
        )
        
        if result:
            logger.info(f"Usuario {user_id} activado exitosamente")
        else:
            logger.warning(f"No se pudo activar usuario {user_id}")
        
        return result
    
    def _generate_temp_password(self, length: int = 12) -> str:
        """Generar password temporal seguro."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
