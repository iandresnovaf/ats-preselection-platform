#!/usr/bin/env python3
"""
Script para generar SECRET_KEY segura para ATS Platform.

Uso:
    python scripts/generate_secret.py
    python scripts/generate_secret.py --env-file backend/.env
"""

import argparse
import secrets
import string
import sys
from pathlib import Path


def generate_secret_key(length: int = 50) -> str:
    """
    Genera una clave secreta segura de alta entropía.
    
    Args:
        length: Longitud de la clave (default: 50 caracteres)
        
    Returns:
        Clave secreta segura (32+ bytes de entropía)
    """
    # Usar secrets para generación criptográficamente segura
    # Combinar letras, números y caracteres especiales
    alphabet = string.ascii_letters + string.digits + "_-"
    
    # Generar clave con alta entropía
    secret_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    return secret_key


def update_env_file(env_path: Path, secret_key: str) -> bool:
    """
    Actualiza o agrega SECRET_KEY en el archivo .env
    
    Args:
        env_path: Ruta al archivo .env
        secret_key: Nueva clave secreta
        
    Returns:
        True si se actualizó correctamente
    """
    if not env_path.exists():
        print(f"❌ Error: No se encontró el archivo {env_path}")
        return False
    
    content = env_path.read_text()
    
    # Buscar línea SECRET_KEY existente
    lines = content.split('\n')
    new_lines = []
    updated = False
    
    for line in lines:
        if line.strip().startswith('SECRET_KEY='):
            # Reemplazar línea existente
            new_lines.append(f'SECRET_KEY={secret_key}')
            updated = True
        else:
            new_lines.append(line)
    
    # Si no se encontró SECRET_KEY, agregar al final
    if not updated:
        new_lines.append(f'\n# Auto-generated secure key')
        new_lines.append(f'SECRET_KEY={secret_key}')
    
    # Guardar archivo actualizado
    env_path.write_text('\n'.join(new_lines))
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Genera SECRET_KEY segura para ATS Platform'
    )
    parser.add_argument(
        '--env-file',
        type=str,
        default='backend/.env',
        help='Ruta al archivo .env (default: backend/.env)'
    )
    parser.add_argument(
        '--length',
        type=int,
        default=50,
        help='Longitud de la clave en caracteres (default: 50)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mostrar clave sin actualizar archivo'
    )
    parser.add_argument(
        '--entropy',
        action='store_true',
        help='Mostrar estimación de entropía'
    )
    
    args = parser.parse_args()
    
    # Generar clave segura
    secret_key = generate_secret_key(args.length)
    
    print("=" * 60)
    print("🔐 ATS Platform - Secret Key Generator")
    print("=" * 60)
    print(f"\n📏 Longitud: {args.length} caracteres")
    print(f"🔑 Clave generada:\n{secret_key}")
    
    if args.entropy:
        # Estimación de entropía (aproximada)
        charset_size = 64  # a-z, A-Z, 0-9, _-
        entropy_bits = args.length * (charset_size.bit_length())
        print(f"\n📊 Entropía estimada: ~{entropy_bits} bits")
        print(f"   (Recomendado: mínimo 256 bits para producción)")
    
    if args.dry_run:
        print("\n📝 Dry-run: No se actualizó ningún archivo")
        print("\n💡 Para usar esta clave, copia el valor a tu .env:")
        print(f"   SECRET_KEY={secret_key}")
    else:
        env_path = Path(args.env_file)
        
        # Buscar desde diferentes directorios
        if not env_path.exists():
            # Intentar desde directorio actual
            alt_paths = [
                Path('.') / args.env_file,
                Path('..') / args.env_file,
                Path(__file__).parent.parent / '.env',
                Path(__file__).parent.parent / 'backend' / '.env',
            ]
            for alt_path in alt_paths:
                if alt_path.exists():
                    env_path = alt_path
                    break
        
        if update_env_file(env_path, secret_key):
            print(f"\n✅ SECRET_KEY actualizado en: {env_path}")
            print("\n⚠️  IMPORTANTE:")
            print("   - No compartas esta clave")
            print("   - En producción, usa variable de entorno:")
            print("     export SECRET_KEY='tu-clave-generada'")
            print("   - Rotar claves periódicamente")
        else:
            print(f"\n❌ No se pudo actualizar {env_path}")
            print(f"\n💡 Copia manualmente esta clave a tu .env:")
            print(f"   SECRET_KEY={secret_key}")
            sys.exit(1)
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
