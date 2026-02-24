#!/usr/bin/env python3
"""
ATS Platform - Pre-Deployment Check Script

Verifica que todo esté configurado correctamente antes de un deploy a producción.
Retorna código de error 0 si todo está bien, 1 si hay errores críticos.

Uso:
    python scripts/pre_deploy_check.py [--strict] [--skip-db]

Opciones:
    --strict    Falla si hay warnings adicionales
    --skip-db   Omite las verificaciones de conexión a DB
"""

import os
import sys
import re
import subprocess
import argparse
from pathlib import Path
from typing import List, Tuple, Optional


class Colors:
    """ANSI color codes para output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class PreDeployChecker:
    """Clase principal para verificaciones pre-deploy"""
    
    # Variables críticas que deben existir
    CRITICAL_VARS = [
        'SECRET_KEY',
        'ENCRYPTION_KEY',
        'DATABASE_URL',
        'REDIS_URL',
        'DEFAULT_ADMIN_EMAIL',
        'DEFAULT_ADMIN_PASSWORD',
        'OPENAI_API_KEY',
    ]
    
    # Variables que NO deben tener valores placeholder
    PLACEHOLDER_PATTERNS = [
        r'CHANGE_ME[_\w]*',
        r'REPLACE_WITH[_\w]*',
        r'STRONG_PASSWORD[_\w]*',
        r'your[_\w]*password[_\w]*',
        r'PLACEHOLDER[_\w]*',
        r'YOUR_[_\w]*_HERE',
        r'sk-PLACEHOLDER',
        r'sk-YOUR_',
    ]
    
    # Secretos que NO deben aparecer en respuestas
    SECRET_PATTERNS = [
        r'sk-[a-zA-Z0-9]{20,}',  # OpenAI API keys
        r'password[=:]\s*\S+',
        r'secret[=:]\s*\S+',
        r'token[=:]\s*\S+',
        r'key[=:]\s*[a-zA-Z0-9]{32,}',
    ]
    
    def __init__(self, strict: bool = False, skip_db: bool = False):
        self.strict = strict
        self.skip_db = skip_db
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.project_root = Path(__file__).parent.parent.absolute()
        
    def log_success(self, message: str):
        """Log mensaje de éxito"""
        print(f"{Colors.GREEN}✓{Colors.END} {message}")
        
    def log_warning(self, message: str):
        """Log warning"""
        print(f"{Colors.YELLOW}⚠{Colors.END} {message}")
        self.warnings.append(message)
        
    def log_error(self, message: str):
        """Log error"""
        print(f"{Colors.RED}✗{Colors.END} {message}")
        self.errors.append(message)
        
    def log_info(self, message: str):
        """Log informativo"""
        print(f"{Colors.BLUE}ℹ{Colors.END} {message}")
        self.info.append(message)
        
    def check_git_env_not_tracked(self) -> bool:
        """Verifica que .env no esté trackeado por git"""
        self.log_info("Verificando que .env no esté en git...")
        
        try:
            # Verificar si .env está en .gitignore
            gitignore_path = self.project_root / '.gitignore'
            if gitignore_path.exists():
                content = gitignore_path.read_text()
                if '.env' in content or '.env.*' in content:
                    self.log_success("Archivos .env están en .gitignore")
                else:
                    self.log_warning("Los archivos .env no están explícitamente en .gitignore")
            
            # Verificar que .env no esté trackeado
            result = subprocess.run(
                ['git', 'ls-files', '.env'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                self.log_error("¡CRÍTICO! Archivo .env está trackeado por git")
                return False
            
            # Verificar otros archivos de environment
            result = subprocess.run(
                ['git', 'ls-files', '*.env', '.env.*'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            tracked_envs = result.stdout.strip().split('\n')
            tracked_envs = [f for f in tracked_envs if f and 'example' not in f.lower()]
            
            if tracked_envs:
                self.log_error(f"¡CRÍTICO! Archivos de environment trackeados: {', '.join(tracked_envs)}")
                return False
            
            self.log_success("No hay archivos .env trackeados por git")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log_warning(f"No se pudo verificar git: {e}")
            return True  # Asumimos OK si no hay git
        except Exception as e:
            self.log_error(f"Error verificando git: {e}")
            return False
    
    def check_env_files_secrets(self) -> bool:
        """Verifica que los archivos .env no tengan placeholders"""
        self.log_info("Verificando archivos de environment...")
        
        env_files = [
            self.project_root / 'backend' / '.env',
            self.project_root / '.env',
            self.project_root / '.env.production',
        ]
        
        all_ok = True
        found_env = False
        
        for env_file in env_files:
            if not env_file.exists():
                continue
                
            found_env = True
            content = env_file.read_text()
            
            for pattern in self.PLACEHOLDER_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Ignorar líneas comentadas
                    line_start = content.rfind('\n', 0, match.start()) + 1
                    line = content[line_start:match.end()].strip()
                    if not line.startswith('#'):
                        self.log_error(f"Placeholder encontrado en {env_file.name}: {match.group()}")
                        all_ok = False
        
        if not found_env:
            self.log_error("No se encontró ningún archivo .env")
            return False
            
        if all_ok:
            self.log_success("No se encontraron placeholders en archivos .env")
        
        return all_ok
    
    def check_critical_env_vars(self) -> bool:
        """Verifica que las variables críticas existan y no estén vacías"""
        self.log_info("Verificando variables de entorno críticas...")
        
        # Cargar variables desde archivos .env
        env_files = [
            self.project_root / 'backend' / '.env',
            self.project_root / '.env',
        ]
        
        env_vars = dict(os.environ)
        
        for env_file in env_files:
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip().strip('"\'')
        
        all_ok = True
        
        for var in self.CRITICAL_VARS:
            value = env_vars.get(var)
            
            if not value:
                self.log_error(f"Variable crítica no configurada: {var}")
                all_ok = False
            elif len(value) < 8:
                self.log_warning(f"Variable {var} parece demasiado corta (< 8 caracteres)")
            elif any(re.match(pattern, value, re.IGNORECASE) for pattern in self.PLACEHOLDER_PATTERNS):
                self.log_error(f"Variable {var} contiene un placeholder")
                all_ok = False
        
        # Verificaciones específicas
        secret_key = env_vars.get('SECRET_KEY', '')
        if len(secret_key) < 32:
            self.log_error("SECRET_KEY debe tener al menos 32 caracteres")
            all_ok = False
        elif secret_key == 'CHANGE_ME_GENERATE_USING_SCRIPTS':
            self.log_error("SECRET_KEY no ha sido generada - usa scripts/generate_secrets.py")
            all_ok = False
        
        # Verificar DATABASE_URL
        db_url = env_vars.get('DATABASE_URL', '')
        if 'CHANGE_ME' in db_url or 'STRONG_PASSWORD' in db_url:
            self.log_error("DATABASE_URL contiene password placeholder")
            all_ok = False
        
        # Verificar DEFAULT_ADMIN_PASSWORD
        admin_pass = env_vars.get('DEFAULT_ADMIN_PASSWORD', '')
        if admin_pass in ['CHANGE_THIS_STRONG_PASSWORD_123!', 'CHANGE_ME_STRONG_PASSWORD_MIN_12_CHARS']:
            self.log_error("DEFAULT_ADMIN_PASSWORD debe ser cambiada")
            all_ok = False
        elif len(admin_pass) < 12:
            self.log_warning("DEFAULT_ADMIN_PASSWORD debería tener al menos 12 caracteres")
        
        # Verificar CORS_ORIGINS
        cors = env_vars.get('CORS_ORIGINS', '')
        if cors == '*':
            self.log_error("CORS_ORIGINS no puede ser '*' en producción")
            all_ok = False
        elif 'localhost' in cors and 'production' in str(self.project_root / '.env'):
            self.log_warning("CORS_ORIGINS contiene localhost en configuración de producción")
        
        if all_ok:
            self.log_success("Todas las variables críticas están configuradas correctamente")
        
        return all_ok
    
    def check_database_connectivity(self) -> bool:
        """Verifica conectividad a la base de datos"""
        if self.skip_db:
            self.log_info("Verificación de DB omitida (--skip-db)")
            return True
            
        self.log_info("Verificando conectividad a base de datos...")
        
        try:
            import asyncpg
            import asyncio
            
            # Obtener DATABASE_URL
            env_vars = dict(os.environ)
            env_file = self.project_root / 'backend' / '.env'
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('DATABASE_URL='):
                            env_vars['DATABASE_URL'] = line.split('=', 1)[1].strip().strip('"\'')
            
            database_url = env_vars.get('DATABASE_URL')
            if not database_url:
                self.log_error("DATABASE_URL no configurada")
                return False
            
            # Convertir a formato asyncpg si es necesario
            db_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
            
            async def test_connection():
                conn = await asyncpg.connect(db_url)
                version = await conn.fetchval('SELECT version()')
                await conn.close()
                return version
            
            version = asyncio.run(test_connection())
            self.log_success(f"Conexión a DB exitosa: {version.split()[0]} {version.split()[1]}")
            return True
            
        except ImportError:
            self.log_warning("asyncpg no instalado, omitiendo verificación de DB")
            return True
        except Exception as e:
            self.log_error(f"No se puede conectar a la base de datos: {e}")
            return False
    
    def check_redis_connectivity(self) -> bool:
        """Verifica conectividad a Redis"""
        if self.skip_db:
            return True
            
        self.log_info("Verificando conectividad a Redis...")
        
        try:
            import redis
            
            # Obtener REDIS_URL
            env_vars = dict(os.environ)
            env_file = self.project_root / 'backend' / '.env'
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('REDIS_URL='):
                            env_vars['REDIS_URL'] = line.split('=', 1)[1].strip().strip('"\'')
            
            redis_url = env_vars.get('REDIS_URL', 'redis://localhost:6379/0')
            
            # Parse URL
            r = redis.from_url(redis_url, socket_connect_timeout=5)
            r.ping()
            info = r.info()
            self.log_success(f"Conexión a Redis exitosa: v{info.get('redis_version', 'unknown')}")
            return True
            
        except ImportError:
            self.log_warning("redis no instalado, omitiendo verificación de Redis")
            return True
        except Exception as e:
            self.log_error(f"No se puede conectar a Redis: {e}")
            return False
    
    def check_dependencies_installed(self) -> bool:
        """Verifica que las dependencias estén instaladas"""
        self.log_info("Verificando dependencias instaladas...")
        
        backend_dir = self.project_root / 'backend'
        requirements_file = backend_dir / 'requirements.txt'
        
        if not requirements_file.exists():
            self.log_warning("No se encontró requirements.txt")
            return True
        
        try:
            # Verificar pip
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list'],
                capture_output=True,
                text=True
            )
            
            installed_packages = result.stdout.lower()
            
            # Leer requirements
            with open(requirements_file) as f:
                requirements = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-'):
                        # Extraer nombre del paquete
                        pkg_name = line.split('==')[0].split('>=')[0].split('<')[0].strip()
                        requirements.append(pkg_name.lower())
            
            missing = []
            critical_packages = ['fastapi', 'sqlalchemy', 'asyncpg', 'redis', 'celery', 'pydantic']
            
            for pkg in critical_packages:
                if pkg not in installed_packages:
                    missing.append(pkg)
            
            if missing:
                self.log_error(f"Paquetes críticos faltantes: {', '.join(missing)}")
                return False
            
            self.log_success("Dependencias críticas instaladas")
            return True
            
        except Exception as e:
            self.log_warning(f"No se pudieron verificar dependencias: {e}")
            return True
    
    def check_docker_available(self) -> bool:
        """Verifica que Docker esté disponible para deploy"""
        self.log_info("Verificando disponibilidad de Docker...")
        
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                self.log_success(f"Docker disponible: {version}")
                
                # Verificar docker-compose
                result = subprocess.run(
                    ['docker', 'compose', 'version'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.log_success(f"Docker Compose disponible: {result.stdout.strip()}")
                else:
                    self.log_warning("Docker Compose plugin no disponible")
                
                return True
            else:
                self.log_warning("Docker no está disponible")
                return False
                
        except FileNotFoundError:
            self.log_warning("Docker no está instalado")
            return False
        except Exception as e:
            self.log_warning(f"Error verificando Docker: {e}")
            return False
    
    def check_security_files(self) -> bool:
        """Verifica archivos de seguridad"""
        self.log_info("Verificando archivos de seguridad...")
        
        security_files = [
            ('.bandit', 'Configuración de Bandit'),
            ('.pre-commit-config.yaml', 'Pre-commit hooks'),
        ]
        
        all_ok = True
        for filename, description in security_files:
            filepath = self.project_root / filename
            if filepath.exists():
                self.log_success(f"{description} encontrado")
            else:
                self.log_warning(f"{description} no encontrado: {filename}")
        
        return all_ok
    
    def check_ssl_certs(self) -> bool:
        """Verifica certificados SSL"""
        self.log_info("Verificando certificados SSL...")
        
        ssl_dirs = [
            self.project_root / 'infrastructure' / 'ssl',
            self.project_root / 'nginx' / 'ssl',
        ]
        
        certs_found = False
        for ssl_dir in ssl_dirs:
            if ssl_dir.exists():
                certs = list(ssl_dir.glob('*.crt')) + list(ssl_dir.glob('*.pem'))
                if certs:
                    self.log_success(f"Certificados SSL encontrados en {ssl_dir}")
                    certs_found = True
        
        if not certs_found:
            self.log_warning("No se encontraron certificados SSL - se usarán certificados auto-generados")
        
        return True
    
    def check_disk_space(self) -> bool:
        """Verifica espacio en disco"""
        self.log_info("Verificando espacio en disco...")
        
        try:
            import shutil
            
            stat = shutil.disk_usage(self.project_root)
            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)
            percent_free = (stat.free / stat.total) * 100
            
            if free_gb < 5:
                self.log_error(f"Espacio libre crítico: {free_gb:.1f}GB ({percent_free:.1f}%)")
                return False
            elif free_gb < 10:
                self.log_warning(f"Espacio libre bajo: {free_gb:.1f}GB ({percent_free:.1f}%)")
            else:
                self.log_success(f"Espacio libre: {free_gb:.1f}GB / {total_gb:.1f}GB ({percent_free:.1f}%)")
            
            return True
            
        except Exception as e:
            self.log_warning(f"No se pudo verificar espacio en disco: {e}")
            return True
    
    def run_all_checks(self) -> Tuple[bool, List[str], List[str]]:
        """Ejecuta todas las verificaciones"""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}  ATS Platform - Pre-Deployment Check{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
        
        checks = [
            ("Git Environment Check", self.check_git_env_not_tracked),
            ("Environment Files", self.check_env_files_secrets),
            ("Critical Environment Variables", self.check_critical_env_vars),
            ("Database Connectivity", self.check_database_connectivity),
            ("Redis Connectivity", self.check_redis_connectivity),
            ("Dependencies", self.check_dependencies_installed),
            ("Docker Availability", self.check_docker_available),
            ("Security Files", self.check_security_files),
            ("SSL Certificates", self.check_ssl_certs),
            ("Disk Space", self.check_disk_space),
        ]
        
        results = []
        for name, check_func in checks:
            print(f"\n{Colors.BOLD}[{name}]{Colors.END}")
            try:
                result = check_func()
                results.append(result)
            except Exception as e:
                self.log_error(f"Error en verificación '{name}': {e}")
                results.append(False)
        
        return all(results), self.errors, self.warnings
    
    def print_summary(self, success: bool):
        """Imprime resumen de resultados"""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}  RESUMEN{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
        
        if self.errors:
            print(f"{Colors.RED}Errores ({len(self.errors)}):{Colors.END}")
            for err in self.errors:
                print(f"  - {err}")
            print()
        
        if self.warnings:
            print(f"{Colors.YELLOW}Advertencias ({len(self.warnings)}):{Colors.END}")
            for warn in self.warnings:
                print(f"  - {warn}")
            print()
        
        if success:
            if self.warnings and self.strict:
                print(f"{Colors.YELLOW}⚠ CHECK FALLIDO (modo estricto){Colors.END}")
                print("Hay advertencias que deben resolverse antes del deploy.\n")
                return False
            else:
                print(f"{Colors.GREEN}✓ TODOS LOS CHECKS PASARON{Colors.END}")
                print("El sistema está listo para deploy.\n")
                return True
        else:
            print(f"{Colors.RED}✗ CHECK FALLIDO{Colors.END}")
            print("Hay errores críticos que deben resolverse antes del deploy.\n")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Pre-deployment checks for ATS Platform'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Fallar también si hay warnings'
    )
    parser.add_argument(
        '--skip-db',
        action='store_true',
        help='Omitir verificaciones de conectividad a DB/Redis'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Output minimalista (solo resultado)'
    )
    
    args = parser.parse_args()
    
    checker = PreDeployChecker(strict=args.strict, skip_db=args.skip_db)
    success, errors, warnings = checker.run_all_checks()
    
    if not args.quiet:
        final_success = checker.print_summary(success)
    else:
        final_success = success and not (args.strict and warnings)
    
    sys.exit(0 if final_success else 1)


if __name__ == '__main__':
    main()
