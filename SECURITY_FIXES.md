# Security Fixes - Resumen de Cambios

## 1. Migración de python-jose a PyJWT ✅

### Archivos modificados:
- `backend/requirements.txt`: Reemplazado `python-jose==3.3.0` por `PyJWT==2.8.0`
- `backend/app/core/auth.py`: 
  - Cambiado `from jose import JWTError, jwt` por `import jwt` y `from jwt.exceptions import PyJWTError`
  - Actualizado `decode_token()` para capturar `PyJWTError` en lugar de `JWTError`
- `backend/app/core/rate_limit.py`: Actualizado imports de jwt
- `backend/tests/test_auth.py`: Cambiado `from jose import jwt` por `import jwt`
- `backend/tests/test_auth_security.py`: Cambiado `from jose import jwt` por `import jwt`

### Verificación:
```bash
cd backend
source venv/bin/activate
python -c "from app.core.auth import create_access_token, decode_token; print('✅ PyJWT funciona')"
```

## 2. Actualización de Dependencias Vulnerables ✅

### Versiones actualizadas en requirements.txt:
- `cryptography>=43.0.0` (anterior: 42.0.0)
- `python-multipart>=0.0.9` (anterior: 0.0.6)
- `fastapi>=0.115.0` (anterior: 0.109.0)
- `PyJWT==2.8.0` (reemplaza python-jose)

### Instalación:
```bash
pip install -r requirements.txt
```

## 3. Mejoras en Content Security Policy (CSP) ✅

### Cambios en `backend/app/main.py`:
- CSP estricto para producción (sin 'unsafe-inline' ni 'unsafe-eval')
- CSP relajado para desarrollo (donde se usa Swagger UI)
- Documentación de qué scripts necesitan excepciones:
  - Swagger UI en /docs y /redoc usa 'unsafe-inline' y 'unsafe-eval' para inicialización
  - En producción con DEBUG=False, estos endpoints están desactivados

### Headers de seguridad mejorados:
- `upgrade-insecure-requests` en producción
- `frame-ancestors 'none'` para prevenir clickjacking
- `object-src 'none'` para prevenir contenido Flash/PDF embebido

## 4. Workflow de SAST (GitHub Actions) ✅

### Archivo creado: `.github/workflows/security.yml`

Incluye:
1. **Bandit**: Análisis estático de seguridad Python
   - Escanea el directorio `backend/app`
   - Falla el build si encuentra vulnerabilidades CRITICAL/HIGH
   - Genera reporte SARIF para GitHub Security tab

2. **Safety**: Chequeo de vulnerabilidades en dependencias
   - Escanea `requirements.txt`
   - Falla si encuentra vulnerabilidades con CVSS >= 7.0

3. **TruffleHog**: Detección de secretos
   - Escanea el historial de git
   - Detecta API keys, tokens, contraseñas

4. **flake8-security**: Linting de seguridad
   - Ejecuta bandit como plugin de flake8
   - Falla si encuentra issues de seguridad

5. **pip-audit**: Auditoría de dependencias
   - Usa base de datos de vulnerabilidades
   - Reporte en formato JSON

### Configuración:
- Se ejecuta en push/PR a main y develop
- Ejecución diaria programada (cron)
- Fails fast en vulnerabilidades críticas

## 5. Validación de UUIDs ✅

### Archivos modificados:
- `backend/app/core/deps.py`: Agregadas funciones:
  - `validate_uuid(uuid_str)`: Valida y convierte string a UUID
  - `validate_uuid_param(param_name)`: Helper para path parameters

- `backend/app/main.py`: Agregado exception handler:
  - `is_uuid_validation_error()`: Detecta si un error es de UUID
  - `extract_uuid_param_name()`: Extrae nombre del parámetro
  - `validation_exception_handler()`: Convierte errores 422 a 400 para UUIDs inválidos

- `backend/app/api/v1/candidates.py`: Actualizado para usar validación explícita

### Comportamiento:
- Antes: UUID inválido retornaba 422 Unprocessable Entity
- Ahora: UUID inválido retorna 400 Bad Request con mensaje claro

### Ejemplo:
```
GET /candidates/invalid-uuid
Response: 400 Bad Request
{
    "detail": "UUID inválido en parámetro 'candidate_id'. Debe ser un UUID válido (ej: 550e8400-e29b-41d4-a716-446655440000)",
    "error_code": "INVALID_UUID",
    "parameter": "candidate_id"
}
```

## Archivos de configuración de seguridad existentes:
- `.bandit`: Configuración de Bandit SAST
- `.pre-commit-config.yaml`: Hooks de pre-commit (incluye seguridad)
- `.github/dependabot.yml`: Escaneo automático de dependencias

## Comandos de verificación:

```bash
# 1. Verificar instalación de dependencias
cd backend
pip install -r requirements.txt

# 2. Verificar imports
python -c "from app.core.auth import *; from app.core.deps import *; print('OK')"

# 3. Ejecutar bandit localmente
pip install bandit
bandit -r app -ll

# 4. Ejecutar tests de autenticación
cd backend
pytest tests/test_auth.py -v

# 5. Verificar sintaxis YAML del workflow
pip install yamllint
yamllint .github/workflows/security.yml
```

## Notas de implementación:

1. **PyJWT vs python-jose**: PyJWT es la librería oficial del proyecto JWT y está mejor mantenida. La API es similar pero los nombres de excepciones cambian (`JWTError` → `PyJWTError`).

2. **CSP**: La directiva 'unsafe-inline' es necesaria para Swagger UI pero solo está habilitada en modo DEBUG. En producción se usa un CSP estricto.

3. **UUIDs**: FastAPI con Pydantic valida UUIDs automáticamente, pero retorna 422. El exception handler convierte estos errores a 400 para mejor semántica HTTP.

4. **Workflow SAST**: Configurado para fallar solo en vulnerabilidades CRITICAL/HIGH. Las de severidad media/baja se reportan pero no bloquean el build.
