#!/usr/bin/env python3
"""
ATS Platform - Secret Setup Script
====================================
Script de configuración inicial de secretos y seguridad.

Uso:
    python scripts/setup_secrets.py              # Configuración interactiva
    python scripts/setup_secrets.py --check      # Validar configuración actual
    python scripts/setup_secrets.py --force      # Sobrescribir .env existente

Este script:
1. Valida que .env no esté trackeado por git
2. Genera SECRET_KEY aleatorio seguro
3. Genera contraseñas seguras para DB y admin
4. Crea .env a partir de .env.example
"""

import os
import sys
import re
import secrets
import string
import subprocess
from pathlib import Path
from cryptography.fernet import Fernet


class Colors:
    """Colores para terminal."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header():
    """Imprime encabezado."""
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("=" * 70)
    print("🔐  ATS Platform - Secret Setup")
    print("=" * 70)
    print(f"{Colors.END}")
    print()


def print_success(msg):
    """Imprime mensaje de éxito."""
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")


def print_error(msg):
    """Imprime mensaje de error."""
    print(f"{Colors.RED}❌ {msg}{Colors.END}")


def print_warning(msg):
    """Imprime mensaje de advertencia."""
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")


def print_info(msg):
    """Imprime mensaje informativo."""
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")


def generate_secret_key(length=64):
    """Genera SECRET_KEY criptográficamente seguro."""
    alphabet = string.ascii_letters + string.digits + "_-"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_encryption_key():
    """Genera clave Fernet para encriptación."""
    return Fernet.generate_key().decode()


def generate_strong_password(length=24):
    """Genera contraseña fuerte."""
    # Asegurar al menos un carácter de cada tipo
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*()-_=+[]{}|;:,.<>?"),
    ]
    
    # Completar
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    password.extend(secrets.choice(alphabet) for _ in range(length - 4))
    
    # Mezclar
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


def check_git_tracking(env_path):
    """Verifica si el archivo .env está siendo trackeado por git."""
    try:
        result = subprocess.run(
            ['git', 'ls-files', env_path],
            capture_output=True,
            text=True,
            cwd=Path(env_path).parent
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:
        return False


def validate_env_content(env_path):
    """Valida el contenido del archivo .env."""
    issues = []
    
    if not os.path.exists(env_path):
        return [f"Archivo no encontrado: {env_path}"]
    
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
    placeholders = [
        'CHANGE_ME', 'changeme', 'password', 'secret', 'YOUR_',
        'REPLACE_', 'EXAMPLE', 'DEFAULT', '123456', 'admin'
    ]
    
    critical_vars = ['SECRET_KEY', 'DEFAULT_ADMIN_PASSWORD']
    for var in critical_vars:
        if var in env_vars:
            value = env_vars[var]
            for placeholder in placeholders:
                if placeholder.lower() in value.lower():
                    issues.append(f"{var} contiene valor placeholder: '{placeholder}'")
                    break
            if len(value) < 12:
                issues.append(f"{var} es muy corto ({len(value)} chars, mínimo 12)")
    
    # Validar DATABASE_URL
    db_url = env_vars.get('DATABASE_URL', '')
    if 'CHANGE_ME' in db_url or 'password' in db_url.lower():
        issues.append("DATABASE_URL contiene password placeholder")
    
    # Validar DEBUG en producción
    if env_vars.get('ENVIRONMENT') == 'production':
        if env_vars.get('DEBUG', '').lower() == 'true':
            issues.append("DEBUG=true en entorno de producción")
    
    return issues


def create_env_file(example_path, output_path, force=False):
    """Crea archivo .env a partir de .env.example."""
    
    # Verificar si ya existe
    if os.path.exists(output_path) and not force:
        print_warning(f"El archivo {output_path} ya existe")
        response = input(f"{Colors.YELLOW}¿Sobrescribir? Se perderán los valores actuales (s/N): {Colors.END}").strip().lower()
        if response != 's':
            print_info("Operación cancelada")
            return False
    
    # Leer template
    with open(example_path, 'r') as f:
        content = f.read()
    
    print_info("Generando secrets criptográficamente seguros...")
    
    # Generar valores
    secret_key = generate_secret_key(64)
    encryption_key = generate_encryption_key()
    admin_password = generate_strong_password(24)
    db_password = generate_strong_password(24)
    
    # Reemplazar placeholders
    replacements = [
        (r'SECRET_KEY=.*', f'SECRET_KEY={secret_key}'),
        (r'ENCRYPTION_KEY=.*', f'ENCRYPTION_KEY={encryption_key}'),
        (r'DEFAULT_ADMIN_PASSWORD=.*', f'DEFAULT_ADMIN_PASSWORD={admin_password}'),
        (r'postgresql\+asyncpg://postgres:[^@]+@', f'postgresql+asyncpg://postgres:{db_password}@'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, count=1)
    
    # Guardar archivo
    with open(output_path, 'w') as f:
        f.write(content)
    
    # Establecer permisos seguros (solo owner puede leer/escribir)
    os.chmod(output_path, 0o600)
    
    return True


def main():
    """Función principal."""
    args = sys.argv[1:]
    check_mode = '--check' in args
    force_mode = '--force' in args
    
    print_header()
    
    # Determinar rutas
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    example_path = project_root / '.env.example'
    env_path = project_root / 'backend' / '.env'
    
    # Modo validación
    if check_mode:
        print_info(f"Validando configuración en: {env_path}")
        print()
        
        issues = validate_env_content(env_path)
        
        if issues:
            for issue in issues:
                print_error(issue)
            print()
            print_error(f"Se encontraron {len(issues)} problemas de seguridad")
            sys.exit(1)
        else:
            print_success("Todas las validaciones de seguridad pasaron")
            sys.exit(0)
    
    # Verificar que .env.example existe
    if not example_path.exists():
        print_error(f"No se encontró {example_path}")
        print_info("Asegúrate de ejecutar este script desde el directorio del proyecto")
        sys.exit(1)
    
    # Verificar que .env no esté trackeado por git
    print_info("Verificando que .env no esté en control de versiones...")
    if check_git_tracking(env_path):
        print_error("¡ALERTA DE SEGURIDAD!")
        print_error(f"El archivo {env_path} está siendo trackeado por git")
        print()
        print(f"{Colors.YELLOW}Para removerlo de git (pero mantenerlo localmente):{Colors.END}")
        print(f"  git rm --cached {env_path}")
        print(f"  echo '.env' >> .gitignore")
        print(f"  git commit -m 'Remove .env from tracking'")
        print()
        response = input(f"{Colors.YELLOW}¿Continuar de todos modos? (s/N): {Colors.END}").strip().lower()
        if response != 's':
            sys.exit(1)
    else:
        print_success("Archivo .env no está trackeado por git")
    
    print()
    
    # Crear archivo .env
    print_info(f"Creando configuración en: {env_path}")
    
    # Asegurar que el directorio backend existe
    env_path.parent.mkdir(parents=True, exist_ok=True)
    
    if create_env_file(example_path, env_path, force_mode):
        print()
        print_success(f"Archivo .env creado exitosamente")
        print_info(f"Permisos establecidos: 600 (solo propietario)")
        print()
        
        # Leer y mostrar valores generados
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Extraer valores generados
        secret_key = re.search(r'SECRET_KEY=(.+)', content)
        admin_pwd = re.search(r'DEFAULT_ADMIN_PASSWORD=(.+)', content)
        
        print(f"{Colors.CYAN}{Colors.BOLD}Secrets generados:{Colors.END}")
        print(f"  SECRET_KEY: {secret_key.group(1)[:20]}..." if secret_key else "  SECRET_KEY: [no encontrado]")
        print(f"  DEFAULT_ADMIN_PASSWORD: {'*' * 12}")
        print()
        
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  IMPORTANTE:{Colors.END}")
        print("   1. Revisa y actualiza DATABASE_URL con tus credenciales reales")
        print("   2. Agrega tu OPENAI_API_KEY si usas funciones de IA")
        print("   3. Configura las variables de WhatsApp si es necesario")
        print("   4. NO compartas este archivo ni lo subas a git")
        print("   5. Mantén un backup seguro de estas claves")
        print("   6. Ejecuta 'python scripts/setup_secrets.py --check' para validar")
        print()
        
        print_success("Setup completado!")
    else:
        print_info("No se realizaron cambios")


if __name__ == "__main__":
    main()
