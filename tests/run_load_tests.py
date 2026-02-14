#!/usr/bin/env python3
"""
Script de ejecución de Load Tests
=================================
Facilita la ejecución de tests de carga con diferentes configuraciones.

Uso:
    python run_load_tests.py smoke_load
    python run_load_tests.py medium_load --host http://staging.example.com
    python run_load_tests.py --list
"""

import argparse
import subprocess
import sys
import os
from datetime import datetime

# Añadir parent al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.load.config import LOAD_TEST_CONFIGS, get_load_test_command


def list_configs():
    """Lista todas las configuraciones disponibles."""
    print("=" * 70)
    print("LOAD TEST CONFIGURATIONS")
    print("=" * 70)
    
    for name, config in LOAD_TEST_CONFIGS.items():
        print(f"\n📋 {name}")
        print(f"   Description: {config['description']}")
        print(f"   Users: {config['users']}")
        print(f"   Spawn Rate: {config['spawn_rate']}/s")
        print(f"   Duration: {config['duration']}")
    
    print("\n" + "=" * 70)


def run_load_test(config_name: str, host: str = None, report_dir: str = "reports"):
    """Ejecuta un test de carga."""
    if config_name not in LOAD_TEST_CONFIGS:
        print(f"❌ Error: Configuración '{config_name}' no encontrada")
        print(f"Disponibles: {', '.join(LOAD_TEST_CONFIGS.keys())}")
        sys.exit(1)
    
    config = LOAD_TEST_CONFIGS[config_name]
    host = host or os.getenv("TEST_BASE_URL", "http://localhost:8000")
    
    print("=" * 70)
    print(f"LOAD TEST: {config_name}")
    print("=" * 70)
    print(f"Description: {config['description']}")
    print(f"Host: {host}")
    print(f"Users: {config['users']}")
    print(f"Spawn Rate: {config['spawn_rate']}/s")
    print(f"Duration: {config['duration']}")
    print("=" * 70)
    print()
    
    # Crear directorio de reports
    os.makedirs(report_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_prefix = f"{report_dir}/load_test_{config_name}_{timestamp}"
    
    # Construir comando
    cmd = [
        "locust",
        "-f", "tests/load/locustfile.py",
        "--host", host,
        "-u", str(config['users']),
        "-r", str(config['spawn_rate']),
        "-t", config['duration'],
        "--headless",
        "--csv", report_prefix
    ]
    
    if "user_class" in config:
        cmd.extend(["--class-picker", config['user_class']])
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    # Ejecutar
    try:
        result = subprocess.run(cmd, check=True)
        print()
        print("=" * 70)
        print(f"✅ Load test completed: {config_name}")
        print(f"📊 Reports saved to: {report_prefix}_*.csv")
        print("=" * 70)
        return 0
    except subprocess.CalledProcessError as e:
        print()
        print("=" * 70)
        print(f"❌ Load test failed: {config_name}")
        print(f"Error: {e}")
        print("=" * 70)
        return 1
    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print(f"⚠️ Load test interrupted: {config_name}")
        print("=" * 70)
        return 130


def main():
    parser = argparse.ArgumentParser(
        description="Run load tests for ATS Platform"
    )
    parser.add_argument(
        "config",
        nargs="?",
        help="Configuration name (e.g., smoke_load, medium_load)"
    )
    parser.add_argument(
        "--host",
        help="Target host URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available configurations"
    )
    parser.add_argument(
        "--report-dir",
        default="reports",
        help="Directory for test reports (default: reports)"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_configs()
        return 0
    
    if not args.config:
        print("Error: Config name required. Use --list to see available configs.")
        return 1
    
    return run_load_test(args.config, args.host, args.report_dir)


if __name__ == "__main__":
    sys.exit(main())
