"""Servicio de gestión de usuarios."""
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
        # Verificar email único
        existing = await self.get_by_email(data.email)
        if existing:
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
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        # Guardar cambios para logging
        changes = {}
        
        # Verificar email único si se cambia
        if data.email and data.email.lower() != user.email:
            existing = await self.get_by_email(data.email)
            if existing:
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
        if data.role and data.role != user.role.value:
            changes['role'] = {"old": user.role.value, "new": data.role}
            user.role = UserRole(data.role)
        if data.status and data.status != user.status.value:
            changes['status'] = {"old": user.status.value, "new": data.status}
            user.status = UserStatus(data.status)
        
        user.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(user)
        
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
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        await self.db.flush()
        
        # Loggear cambio de contraseña por admin
        if self.request and performed_by and performed_by != user_id:
            await self.security_logger.log_user_modification(
                self.request,
                action="password_reset_by_admin",
                target_user_id=user_id,
                performed_by=performed_by
            )
        
        return True
    
    async def deactivate_user(self, user_id: str) -> Optional[User]:
        """Desactivar usuario (soft delete)."""
        return await self.update_user(
            user_id,
            UserUpdate(status=UserStatus.INACTIVE.value)
        )
    
    async def activate_user(self, user_id: str) -> Optional[User]:
        """Activar usuario."""
        return await self.update_user(
            user_id,
            UserUpdate(status=UserStatus.ACTIVE.value)
        )
    
    def _generate_temp_password(self, length: int = 12) -> str:
        """Generar password temporal seguro."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
