"""
Load Tests - Configuración y Scripts de Ejecución
=================================================

Este módulo contiene configuraciones predefinidas para tests de carga.
"""

import os

# Configuraciones predefinidas
LOAD_TEST_CONFIGS = {
    "smoke_load": {
        "description": "Verificación básica de rendimiento (10 usuarios, 1 minuto)",
        "users": 10,
        "spawn_rate": 2,
        "duration": "1m",
        "expected_rps": 10
    },
    "medium_load": {
        "description": "Carga media (50 usuarios, 5 minutos)",
        "users": 50,
        "spawn_rate": 5,
        "duration": "5m",
        "expected_rps": 50
    },
    "heavy_load": {
        "description": "Carga pesada (100 usuarios, 10 minutos)",
        "users": 100,
        "spawn_rate": 10,
        "duration": "10m",
        "expected_rps": 100
    },
    "stress_test": {
        "description": "Stress test (200 usuarios, 15 minutos)",
        "users": 200,
        "spawn_rate": 20,
        "duration": "15m",
        "expected_rps": 200
    },
    "matching_load": {
        "description": "Test específico de matching (50 req/min)",
        "users": 50,
        "spawn_rate": 5,
        "duration": "10m",
        "expected_rps": 50,
        "user_class": "MatchingUser"
    }
}

# Umbrales de rendimiento
PERFORMANCE_THRESHOLDS = {
    "response_time_p95": 2000,  # 95% de requests deben ser < 2s
    "response_time_p99": 5000,  # 99% de requests deben ser < 5s
    "error_rate_max": 0.05,      # Máximo 5% de errores
    "rps_min": 10                # Mínimo 10 requests por segundo
}


def get_load_test_command(config_name: str, host: str = None) -> str:
    """
    Genera el comando para ejecutar un test de carga.
    
    Args:
        config_name: Nombre de la configuración
        host: URL base (default: http://localhost:8000)
    
    Returns:
        Comando listo para ejecutar
    """
    if config_name not in LOAD_TEST_CONFIGS:
        raise ValueError(f"Configuración '{config_name}' no encontrada. "
                        f"Disponibles: {list(LOAD_TEST_CONFIGS.keys())}")
    
    config = LOAD_TEST_CONFIGS[config_name]
    host = host or os.getenv("TEST_BASE_URL", "http://localhost:8000")
    
    cmd = (
        f"locust -f tests/load/locustfile.py "
        f"--host={host} "
        f"-u {config['users']} "
        f"-r {config['spawn_rate']} "
        f"-t {config['duration']} "
        f"--headless "
        f"--csv=reports/load_test_{config_name}"
    )
    
    if "user_class" in config:
        cmd += f" --class-picker {config['user_class']}"
    
    return cmd


def validate_performance_results(stats: dict) -> dict:
    """
    Valida los resultados de un test de carga contra umbrales.
    
    Args:
        stats: Diccionario con estadísticas del test
    
    Returns:
        Dict con validación y recomendaciones
    """
    results = {
        "passed": True,
        "checks": [],
        "recommendations": []
    }
    
    # Check response time p95
    if stats.get("p95_response_time", 0) > PERFORMANCE_THRESHOLDS["response_time_p95"]:
        results["checks"].append({
            "name": "Response Time P95",
            "status": "FAILED",
            "value": f"{stats['p95_response_time']}ms",
            "threshold": f"{PERFORMANCE_THRESHOLDS['response_time_p95']}ms"
        })
        results["passed"] = False
        results["recommendations"].append(
            "Considerar implementar cache o escalar horizontalmente"
        )
    else:
        results["checks"].append({
            "name": "Response Time P95",
            "status": "PASSED",
            "value": f"{stats['p95_response_time']}ms",
            "threshold": f"{PERFORMANCE_THRESHOLDS['response_time_p95']}ms"
        })
    
    # Check error rate
    error_rate = stats.get("error_rate", 0)
    if error_rate > PERFORMANCE_THRESHOLDS["error_rate_max"]:
        results["checks"].append({
            "name": "Error Rate",
            "status": "FAILED",
            "value": f"{error_rate:.2%}",
            "threshold": f"{PERFORMANCE_THRESHOLDS['error_rate_max']:.2%}"
        })
        results["passed"] = False
        results["recommendations"].append(
            "Revisar logs de errores y estabilidad de servicios"
        )
    else:
        results["checks"].append({
            "name": "Error Rate",
            "status": "PASSED",
            "value": f"{error_rate:.2%}",
            "threshold": f"{PERFORMANCE_THRESHOLDS['error_rate_max']:.2%}"
        })
    
    return results


if __name__ == "__main__":
    # Print comandos disponibles
    print("Available Load Test Configurations:")
    print("=" * 50)
    
    for name, config in LOAD_TEST_CONFIGS.items():
        print(f"\n{name}:")
        print(f"  Description: {config['description']}")
        print(f"  Users: {config['users']}")
        print(f"  Duration: {config['duration']}")
        print(f"  Command: {get_load_test_command(name)}")
