#!/usr/bin/env python3
"""
Script para crear un usuario admin inicial.

Uso:
    python create_admin.py                    # Solicita contraseña interactivamente
    python create_admin.py --generate         # Genera contraseña aleatoria segura
    python create_admin.py --password "pwd"   # Especifica contraseña (no recomendado)

Este script ya no usa contraseñas hardcodeadas por seguridad.
"""
import argparse
import asyncio
import sys
import secrets
import string
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.services.user_service import UserService
from app.schemas import UserCreate
from app.models import UserRole


def generate_secure_password(length=16):
    """Genera contraseña segura aleatoria."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Validar que cumple requisitos básicos
        if (any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%^&*" for c in password)):
            return password


def validate_password(password):
    """Valida que la contraseña sea segura."""
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    if not (has_lower and has_upper and has_digit):
        return False, "La contraseña debe contener mayúsculas, minúsculas y números"
    
    return True, "Contraseña válida"


async def create_admin_user(email=None, full_name=None, password=None, generate_password=False):
    """Crear usuario admin inicial."""
    
    # Valores por defecto
    email = email or "admin@topmanagement.cl"
    full_name = full_name or "Super Administrador"
    
    # Determinar contraseña
    if generate_password:
        password = generate_secure_password(16)
        print(f"🔐 Contraseña generada automáticamente")
    elif password is None:
        # Modo interactivo
        import getpass
        print(f"Creando usuario admin: {email}")
        print()
        
        while True:
            password = getpass.getpass("Ingrese contraseña para el admin: ")
            confirm = getpass.getpass("Confirme la contraseña: ")
            
            if password != confirm:
                print("❌ Las contraseñas no coinciden. Intente nuevamente.")
                print()
                continue
            
            is_valid, msg = validate_password(password)
            if not is_valid:
                print(f"❌ {msg}")
                print()
                continue
            
            break
    
    async with async_session_maker() as session:
        user_service = UserService(session)
        
        try:
            # Verificar si ya existe
            existing = await user_service.get_by_email(email)
            if existing:
                print(f"⚠️  Usuario admin ya existe:")
                print(f"   Email: {existing.email}")
                print(f"   Rol: {existing.role}")
                print(f"   Status: {existing.status}")
                return
            
            # Crear usuario admin
            user_data = UserCreate(
                email=email,
                full_name=full_name,
                password=password,
                role="super_admin"
            )
            
            user = await user_service.create_user(user_data)
            await session.commit()
            
            print()
            print("=" * 60)
            print("✅ Usuario admin creado exitosamente:")
            print("=" * 60)
            print(f"   Email: {email}")
            print(f"   Password: {'*' * len(password) if not generate_password else password}")
            print(f"   Rol: super_admin")
            print("=" * 60)
            
            if generate_password:
                print()
                print("⚠️  IMPORTANTE: Guarda esta contraseña en un lugar seguro.")
                print("   No podrás verla nuevamente.")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(
        description='Crea usuario administrador inicial para ATS Platform'
    )
    parser.add_argument(
        '--email',
        default='admin@topmanagement.cl',
        help='Email del administrador (default: admin@topmanagement.cl)'
    )
    parser.add_argument(
        '--full-name',
        default='Super Administrador',
        help='Nombre completo del administrador'
    )
    parser.add_argument(
        '--password',
        help='Contraseña (no recomendado - usar modo interactivo o --generate)'
    )
    parser.add_argument(
        '--generate',
        action='store_true',
        help='Genera contraseña segura automáticamente'
    )
    
    args = parser.parse_args()
    
    # Advertencia si se usa --password
    if args.password:
        print("⚠️  Advertencia: Pasar contraseña por línea de comandos no es seguro")
        print("   Preferir modo interactivo o --generate")
        print()
    
    asyncio.run(create_admin_user(
        email=args.email,
        full_name=args.full_name,
        password=args.password,
        generate_password=args.generate
    ))


if __name__ == "__main__":
    main()
