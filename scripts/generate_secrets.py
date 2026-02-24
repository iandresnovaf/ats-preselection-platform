#!/usr/bin/env python3
"""
Script de Generación de Secrets para Producción
Genera claves criptográficas seguras para el archivo .env

Uso:
    python scripts/generate_secrets.py
    python scripts/generate_secrets.py --output .env.production
    python scripts/generate_secrets.py --check .env.production
"""

import os
import sys
import re
import secrets
import string
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Optional, Tuple, List


class SecretGenerator:
    """Generador de secrets criptográficamente seguros."""
    
    MIN_SECRET_LENGTH = 32
    MIN_PASSWORD_LENGTH = 16
    
    def __init__(self):
        self.issues: List[str] = []
    
    def generate_secret_key(self, length: int = 64) -> str:
        """
        Genera una SECRET_KEY segura para JWT/tokens.
        
        Args:
            length: Longitud mínima de la clave (default 64)
            
        Returns:
            String aleatorio seguro
        """
        # Usar secrets para generación criptográficamente segura
        alphabet = string.ascii_letters + string.digits + "_-"
        return ''.join(secrets.choice(alphabet) for _ in range(max(length, self.MIN_SECRET_LENGTH)))
    
    def generate_encryption_key(self) -> str:
        """
        Genera una clave Fernet para encriptación simétrica.
        
        Returns:
            Clave Fernet válida (base64 de 32 bytes)
        """
        return Fernet.generate_key().decode()
    
    def generate_strong_password(self, length: int = 24) -> str:
        """
        Genera una contraseña fuerte.
        
        Args:
            length: Longitud de la contraseña (default 24)
            
        Returns:
            Contraseña segura
        """
        if length < self.MIN_PASSWORD_LENGTH:
            length = self.MIN_PASSWORD_LENGTH
            
        # Asegurar al menos un carácter de cada tipo
        password = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*()-_=+[]{}|;:,.<>?"),
        ]
        
        # Completar con caracteres aleatorios
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
        password.extend(secrets.choice(alphabet) for _ in range(length - 4))
        
        # Mezclar
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)
    
    def validate_secret_strength(self, secret: str, name: str = "SECRET") -> bool:
        """
        Valida la fortaleza de un secret.
        
        Args:
            secret: El secret a validar
            name: Nombre del secret para mensajes
            
        Returns:
            True si es válido, False si no
        """
        is_valid = True
        
        if not secret or secret.strip() == "":
            self.issues.append(f"❌ {name} está vacío")
            return False
        
        if len(secret) < self.MIN_SECRET_LENGTH:
            self.issues.append(f"❌ {name} es muy corto ({len(secret)} chars, mínimo {self.MIN_SECRET_LENGTH})")
            is_valid = False
        
        # Verificar que no sea un valor de placeholder
        placeholders = [
            "changeme", "change_me", "password", "secret", "key",
            "REPLACE", "EXAMPLE", "DEFAULT", "123456", "admin"
        ]
        secret_lower = secret.lower()
        for placeholder in placeholders:
            if placeholder in secret_lower:
                self.issues.append(f"❌ {name} contiene valor inseguro: '{placeholder}'")
                is_valid = False
                break
        
        # Entropía estimada
        unique_chars = len(set(secret))
        if unique_chars < 10:
            self.issues.append(f"⚠️  {name} tiene baja entropía ({unique_chars} caracteres únicos)")
        
        return is_valid
    
    def validate_env_file(self, env_path: str) -> Tuple[bool, List[str]]:
        """
        Valida un archivo .env completo.
        
        Args:
            env_path: Ruta al archivo .env
            
        Returns:
            Tuple de (es_válido, lista_de_issues)
        """
        self.issues = []
        
        if not os.path.exists(env_path):
            self.issues.append(f"❌ Archivo no encontrado: {env_path}")
            return False, self.issues
        
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Extraer variables
        env_vars = {}
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
        
        # Validar variables críticas
        critical_vars = {
            'SECRET_KEY': self.MIN_SECRET_LENGTH,
            'ENCRYPTION_KEY': 32,
            'DEFAULT_ADMIN_PASSWORD': self.MIN_PASSWORD_LENGTH,
        }
        
        for var, min_len in critical_vars.items():
            if var in env_vars:
                self.validate_secret_strength(env_vars[var], var)
            else:
                self.issues.append(f"⚠️  Variable {var} no encontrada")
        
        # Validar DEBUG en producción
        if env_vars.get('ENVIRONMENT') == 'production':
            if env_vars.get('DEBUG', '').lower() == 'true':
                self.issues.append("❌ DEBUG=true en entorno de producción")
            
            # Validar CORS
            cors_origins = env_vars.get('CORS_ORIGINS', '')
            if '*' in cors_origins:
                self.issues.append("❌ CORS_ORIGINS contiene '*' en producción")
            
            # Validar DATABASE_URL
            db_url = env_vars.get('DATABASE_URL', '')
            if 'postgres' in db_url and 'localhost' in db_url and 'STRONG' in db_url:
                self.issues.append("⚠️  DATABASE_URL parece tener password placeholder")
        
        return len(self.issues) == 0, self.issues
    
    def generate_env_content(self, template_path: Optional[str] = None) -> str:
        """
        Genera el contenido de un archivo .env con secrets nuevos.
        
        Args:
            template_path: Ruta a template (opcional)
            
        Returns:
            Contenido del archivo .env
        """
        secret_key = self.generate_secret_key(64)
        encryption_key = self.generate_encryption_key()
        admin_password = self.generate_strong_password(24)
        
        if template_path and os.path.exists(template_path):
            # Leer template y reemplazar
            with open(template_path, 'r') as f:
                content = f.read()
            
            # Reemplazar placeholders
            content = re.sub(
                r'SECRET_KEY=.*',
                f'SECRET_KEY={secret_key}',
                content
            )
            content = re.sub(
                r'ENCRYPTION_KEY=.*',
                f'ENCRYPTION_KEY={encryption_key}',
                content
            )
            content = re.sub(
                r'DEFAULT_ADMIN_PASSWORD=.*',
                f'DEFAULT_ADMIN_PASSWORD={admin_password}',
                content
            )
            return content
        else:
            # Generar desde cero
            return f"""# ============================================
# ATS Platform - Generated Secrets
# Generated: {self._get_timestamp()}
# ============================================

ENVIRONMENT=production
DEBUG=false

# Security Keys (AUTO-GENERATED)
SECRET_KEY={secret_key}
ENCRYPTION_KEY={encryption_key}

# Admin User (CHANGE EMAIL AS NEEDED)
DEFAULT_ADMIN_EMAIL=admin@yourdomain.com
DEFAULT_ADMIN_PASSWORD={admin_password}

# Database (UPDATE WITH YOUR CREDENTIALS)
DATABASE_URL=postgresql+asyncpg://ats_user:CHANGE_DB_PASSWORD@localhost:5432/ats_platform

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI (ADD YOUR API KEY)
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY_HERE
"""
    
    def _get_timestamp(self) -> str:
        """Obtiene timestamp actual."""
        from datetime import datetime
        return datetime.now().isoformat()


def print_header():
    """Imprime encabezado del script."""
    print("=" * 60)
    print("🔐 ATS Platform - Secret Generator")
    print("=" * 60)
    print()


def print_help():
    """Imprime ayuda."""
    print("Uso:")
    print("  python scripts/generate_secrets.py              # Genera nuevos secrets")
    print("  python scripts/generate_secrets.py --output .env.production")
    print("  python scripts/generate_secrets.py --check .env.production")
    print()
    print("Opciones:")
    print("  --output FILE    Guarda secrets en FILE")
    print("  --check FILE     Valida secrets en FILE")
    print("  --template FILE  Usa FILE como template")
    print("  --help           Muestra esta ayuda")
    print()


def main():
    """Función principal."""
    args = sys.argv[1:]
    
    if '--help' in args or '-h' in args:
        print_help()
        return
    
    generator = SecretGenerator()
    
    # Modo validación
    if '--check' in args:
        check_idx = args.index('--check')
        if check_idx + 1 < len(args):
            env_file = args[check_idx + 1]
            print_header()
            print(f"🔍 Validando: {env_file}")
            print()
            
            is_valid, issues = generator.validate_env_file(env_file)
            
            for issue in issues:
                print(issue)
            
            print()
            if is_valid:
                print("✅ Todas las validaciones pasaron")
                sys.exit(0)
            else:
                print(f"❌ Se encontraron {len(issues)} problemas")
                sys.exit(1)
        else:
            print("❌ Debes especificar el archivo a validar: --check .env")
            sys.exit(1)
    
    # Modo generación
    print_header()
    
    # Determinar output
    output_file = None
    if '--output' in args:
        out_idx = args.index('--output')
        if out_idx + 1 < len(args):
            output_file = args[out_idx + 1]
    
    # Determinar template
    template_file = '.env.production'
    if '--template' in args:
        tpl_idx = args.index('--template')
        if tpl_idx + 1 < len(args):
            template_file = args[tpl_idx + 1]
    
    print("🔑 Generando secrets criptográficamente seguros...")
    print()
    
    # Generar contenido
    env_content = generator.generate_env_content(template_file)
    
    # Guardar o mostrar
    if output_file:
        # Verificar si existe
        if os.path.exists(output_file):
            print(f"⚠️  {output_file} ya existe")
            response = input("¿Sobrescribir? (s/N): ").strip().lower()
            if response != 's':
                print("❌ Cancelado")
                return
        
        # Guardar con permisos restrictivos
        with open(output_file, 'w') as f:
            f.write(env_content)
        
        # Establecer permisos seguros (solo owner puede leer)
        os.chmod(output_file, 0o600)
        
        print(f"✅ Secrets guardados en: {output_file}")
        print(f"   Permisos: 600 (solo propietario)")
    else:
        print("📝 Contenido generado:")
        print("-" * 60)
        print(env_content)
        print("-" * 60)
        print()
        print("💡 Usa --output .env para guardar en archivo")
    
    print()
    print("⚠️  IMPORTANTE:")
    print("   - Revisa y actualiza DATABASE_URL con tus credenciales")
    print("   - Agrega tu OPENAI_API_KEY si usas funciones LLM")
    print("   - NO compartas este archivo ni lo subas a git")
    print("   - Mantén un backup seguro de estas claves")


if __name__ == "__main__":
    main()
