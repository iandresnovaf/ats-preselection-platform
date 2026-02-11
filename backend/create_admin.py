#!/usr/bin/env python3
"""Script para crear un usuario admin inicial para testing."""
import asyncio
import sys
sys.path.insert(0, '/home/andres/.openclaw/workspace/ats-platform/backend')

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.services.user_service import UserService
from app.schemas import UserCreate
from app.models import UserRole

async def create_admin_user():
    """Crear usuario admin inicial."""
    async with async_session_maker() as session:
        user_service = UserService(session)
        
        try:
            # Verificar si ya existe
            existing = await user_service.get_by_email("admin@topmanagement.cl")
            if existing:
                print("✅ Usuario admin ya existe:")
                print(f"   Email: {existing.email}")
                print(f"   Rol: {existing.role}")
                print(f"   Status: {existing.status}")
                return
            
            # Crear usuario admin
            user_data = UserCreate(
                email="admin@topmanagement.cl",
                full_name="Super Administrador",
                password="Admin123!",
                role="super_admin"
            )
            
            user = await user_service.create_user(user_data)
            await session.commit()
            
            print("✅ Usuario admin creado exitosamente:")
            print(f"   Email: admin@topmanagement.cl")
            print(f"   Password: Admin123!")
            print(f"   Rol: super_admin")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(create_admin_user())
