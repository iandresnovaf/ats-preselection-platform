"""
Autorización de objetos - Protección contra IDOR (Insecure Direct Object Reference).
Implementa verificación de ownership a nivel de objeto.
"""
from functools import wraps
from typing import Optional, Callable, Any
from uuid import UUID
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User, UserRole


class AuthorizationError(Exception):
    """Error de autorización."""
    pass


class OwnershipChecker:
    """Verifica ownership de objetos en la base de datos."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_candidate_ownership(
        self, 
        candidate_id: UUID, 
        user: User
    ) -> bool:
        """
        Verifica si un usuario tiene acceso a un candidato.
        
        Por defecto, todos los consultores pueden ver todos los candidatos
        (el modelo de negocio de headhunting es colaborativo).
        Pero se puede restringir por asignación de roles.
        
        Args:
            candidate_id: ID del candidato
            user: Usuario actual
        
        Returns:
            True si tiene acceso
        """
        from app.models.core_ats import HHCandidate, HHApplication, HHRole
        
        # Super admin siempre tiene acceso
        if user.role == UserRole.SUPER_ADMIN:
            return True
        
        # Verificar si el candidato existe
        result = await self.db.execute(
            select(HHCandidate).where(HHCandidate.candidate_id == candidate_id)
        )
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidato no encontrado"
            )
        
        # TODO: Si se implementa asignación específica de candidatos a consultores,
        # verificar aquí. Por ahora, todos los consultores pueden acceder.
        return True
    
    async def check_application_ownership(
        self, 
        application_id: UUID, 
        user: User
    ) -> bool:
        """
        Verifica si un usuario tiene acceso a una aplicación.
        
        Args:
            application_id: ID de la aplicación
            user: Usuario actual
        
        Returns:
            True si tiene acceso
        """
        from app.models.core_ats import HHApplication, HHRole
        
        # Super admin siempre tiene acceso
        if user.role == UserRole.SUPER_ADMIN:
            return True
        
        # Obtener la aplicación con su rol
        result = await self.db.execute(
            select(HHApplication)
            .where(HHApplication.application_id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aplicación no encontrada"
            )
        
        # Verificar si el rol tiene un consultor asignado
        role_result = await self.db.execute(
            select(HHRole).where(HHRole.role_id == application.role_id)
        )
        role = role_result.scalar_one_or_none()
        
        # Si hay un consultor asignado al rol, solo él puede acceder
        # Si no hay consultor asignado, cualquier consultor puede acceder
        # TODO: Implementar assigned_consultant_id en HHRole si es necesario
        
        return True
    
    async def check_role_ownership(
        self, 
        role_id: UUID, 
        user: User
    ) -> bool:
        """
        Verifica si un usuario tiene acceso a un rol/vacante.
        
        Args:
            role_id: ID del rol
            user: Usuario actual
        
        Returns:
            True si tiene acceso
        """
        from app.models.core_ats import HHRole
        
        # Super admin siempre tiene acceso
        if user.role == UserRole.SUPER_ADMIN:
            return True
        
        # Verificar si el rol existe
        result = await self.db.execute(
            select(HHRole).where(HHRole.role_id == role_id)
        )
        role = result.scalar_one_or_none()
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vacante no encontrada"
            )
        
        # TODO: Si se implementa asignación de roles a consultores,
        # verificar aquí
        
        return True
    
    async def check_client_ownership(
        self, 
        client_id: UUID, 
        user: User
    ) -> bool:
        """Verifica acceso a cliente."""
        from app.models.core_ats import HHClient
        
        if user.role == UserRole.SUPER_ADMIN:
            return True
        
        result = await self.db.execute(
            select(HHClient).where(HHClient.client_id == client_id)
        )
        client = result.scalar_one_or_none()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado"
            )
        
        return True


def require_ownership(
    resource_type: str,
    resource_id_param: str = "candidate_id",
    admin_override: bool = True
):
    """
    Decorator para verificar ownership de recursos.
    
    Args:
        resource_type: Tipo de recurso ('candidate', 'application', 'role', 'client')
        resource_id_param: Nombre del parámetro que contiene el ID del recurso
        admin_override: Si True, los admins siempre tienen acceso
    
    Usage:
        @router.get("/{candidate_id}")
        @require_ownership("candidate")
        async def get_candidate(candidate_id: UUID, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extraer db y current_user de los kwargs
            db = kwargs.get('db')
            current_user = kwargs.get('current_user')
            
            if not db or not current_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error de configuración: se requiere db y current_user"
                )
            
            # Extraer resource_id de los kwargs
            resource_id = kwargs.get(resource_id_param)
            if not resource_id:
                # Buscar en args si no está en kwargs
                # Esto es más complejo y depende de la firma de la función
                pass
            
            # Verificar ownership
            checker = OwnershipChecker(db)
            
            try:
                if resource_type == "candidate":
                    has_access = await checker.check_candidate_ownership(
                        UUID(str(resource_id)), current_user
                    )
                elif resource_type == "application":
                    has_access = await checker.check_application_ownership(
                        UUID(str(resource_id)), current_user
                    )
                elif resource_type == "role":
                    has_access = await checker.check_role_ownership(
                        UUID(str(resource_id)), current_user
                    )
                elif resource_type == "client":
                    has_access = await checker.check_client_ownership(
                        UUID(str(resource_id)), current_user
                    )
                else:
                    has_access = True
                
                if not has_access:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No tienes permiso para acceder a este recurso"
                    )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error verificando permisos: {str(e)}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Dependency para verificar ownership en endpoints

async def verify_candidate_access(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> bool:
    """Dependency para verificar acceso a candidato."""
    checker = OwnershipChecker(db)
    return await checker.check_candidate_ownership(candidate_id, current_user)


async def verify_application_access(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> bool:
    """Dependency para verificar acceso a aplicación."""
    checker = OwnershipChecker(db)
    return await checker.check_application_ownership(application_id, current_user)


async def verify_role_access(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> bool:
    """Dependency para verificar acceso a rol."""
    checker = OwnershipChecker(db)
    return await checker.check_role_ownership(role_id, current_user)
