# 🔒 CHECKLIST "MÍNIMAMENTE HACKEABLE" - ATS PLATFORM
## Revisión Final de Seguridad - Fecha: 2026-02-17

---

## 📋 RESUMEN EJECUTIVO

| Categoría | Estado | Críticos | Items |
|-----------|--------|----------|-------|
| **Secretos** | ❌ | 2 | 2 |
| **Mínimo Privilegio** | ❌ | 2 | 3 |
| **Autorización (IDOR)** | ⚠️ | 0 | 2 |
| **Rate Limits/WAF/MFA** | ⚠️ | 1 | 3 |
| **Dependencias** | ⚠️ | 0 | 3 |
| **Observabilidad** | ✅ | 0 | 3 |
| **Backups** | ❌ | 2 | 2 |

### 🚨 Puntuación de Seguridad: **4.5/10** 🔴

---

## 1. NADA DE SECRETOS EN REPOSITORIO

### 1.1 Escaneo de TODO el código con grep/búsqueda de patrones
**Estado:** ❌ **NO CUMPLE**

#### Hallazgos Críticos:

| Archivo | Línea | Secreto | Severidad |
|---------|-------|---------|-----------|
| `backend/.env` | 13 | `SECRET_KEY=rrgLl3EXmuftXFWqCY446fJ4HFhLTfaH_CoG4OH7tGjSsmyek5` | 🔴 CRÍTICO |
| `backend/.env` | 20 | `DEFAULT_ADMIN_PASSWORD=ChangeMe123!` | 🔴 CRÍTICO |
| `docker-compose.yml` | 51 | `DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/ats_platform` | 🟠 ALTO |
| `docker-compose.yml` | 56 | `SECRET_KEY=${SECRET_KEY:-your-secret-key-change-in-production}` | 🟡 MEDIO |

#### Patrones Encontrados:
- ✅ No se encontraron AWS Access Keys (AKIA...)
- ✅ No se encontraron private keys (BEGIN RSA/OPENSSH)
- ✅ No se encontraron OpenAI API keys reales (sk-...)
- ❌ SECRET_KEY hardcodeada en archivo .env
- ❌ Contraseña de admin por defecto hardcodeada

### 1.2 API keys, passwords, tokens, private keys
**Estado:** ❌ **NO CUMPLE**

#### Archivos con secretos:
```bash
# backend/.env - CONTIENE SECRETOS REALES
SECRET_KEY=rrgLl3EXmuftXFWqCY446fJ4HFhLTfaH_CoG4OH7tGjSsmyek5
DEFAULT_ADMIN_PASSWORD=ChangeMe123!
```

#### Plan Urgente:
```bash
# 1. Rotar inmediatamente SECRET_KEY (invalidará todas las sesiones)
# 2. Cambiar DEFAULT_ADMIN_PASSWORD
# 3. Agregar backend/.env a .gitignore
# 4. Usar variables de entorno en producción
# 5. Implementar gestión de secretos (AWS Secrets Manager / HashiCorp Vault)
```

---

## 2. PRINCIPIO DE MÍNIMO PRIVILEGIO

### 2.1 App tiene permisos mínimos en DB
**Estado:** ❌ **NO CUMPLE**

#### Problemas:
```yaml
# docker-compose.yml usa superusuario postgres
postgres:
  environment:
    POSTGRES_USER: postgres      # ❌ Superusuario
    POSTGRES_PASSWORD: postgres  # ❌ Contraseña débil
```

```python
# backend/app/core/database.py
DATABASE_URL = settings.DATABASE_URL  # Sin validación de usuario
```

#### Usuarios que deberían existir:
```sql
-- ❌ NO IMPLEMENTADO
CREATE USER ats_backend WITH PASSWORD 'secure_random_password';
CREATE USER ats_worker WITH PASSWORD 'secure_random_password';

-- Permisos mínimos para backend
GRANT CONNECT ON DATABASE ats_platform TO ats_backend;
GRANT USAGE ON SCHEMA public TO ats_backend;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ats_backend;
```

### 2.2 Credenciales cloud con permisos restrictivos
**Estado:** ❌ **NO CUMPLE**

#### Hallazgos:
- No se detectaron credenciales cloud AWS/Azure/GCP en el código
- No hay configuración de IAM roles
- No hay políticas de acceso configuradas

### 2.3 Usuarios del sistema con acceso limitado
**Estado:** ⚠️ **PARCIAL**

#### Implementado:
```python
# backend/app/core/deps.py tiene RBAC básico
- get_current_user()        # Autenticación
- require_admin()           # Super admin
- require_consultant()      # Consultor/Admin
- require_viewer()          # Viewer/Consultor/Admin
```

#### Falta:
- ❌ Usuarios de sistema (systemd, docker) con permisos limitados
- ❌ Configuración de SELinux/AppArmor
- ❌ Chroot/jail para procesos críticos

---

## 3. VALIDACIÓN DE ENTRADA + AUTORIZACIÓN POR OBJETO (IDOR)

### 3.1 ¿Usuario A puede ver datos de usuario B?
**Estado:** ✅ **CUMPLE PARCIALMENTE**

#### Endpoints verificados:

| Endpoint | Verificación Ownership | Estado |
|----------|------------------------|--------|
| `GET /users/{id}` | Solo admin puede acceder | ✅ |
| `GET /users/me` | Usuario actual | ✅ |
| `GET /candidates/{id}` | Sin verificación de ownership | ⚠️ |
| `GET /jobs/{id}` | Sin verificación de ownership | ⚠️ |
| `GET /jobs/{id}/candidates` | Sin verificación de asignación | ⚠️ |

#### Problema IDOR en jobs:
```python
# backend/app/api/jobs.py
@router.get("/{job_id}")
async def get_job(job_id: str, ...):
    # ❌ NO verifica si el job está asignado al consultor actual
    job = await job_service.get_by_id(job_id)
```

#### Problema IDOR en upload-description:
```python
# Solo verifica admin vs consultor asignado
if current_user.role != "super_admin":
    if str(job.assigned_consultant_id) != str(current_user.id):
        raise HTTPException(status_code=403, ...)
# ✅ CORRECTO - Este sí verifica ownership
```

### 3.2 Verificación de ownership en cada endpoint
**Estado:** ⚠️ **PARCIAL**

#### Endpoints SIN verificación de ownership:
- ❌ `GET /candidates/{id}` - Cualquier viewer puede ver cualquier candidato
- ❌ `GET /jobs/{id}` - Cualquier viewer puede ver cualquier job
- ❌ `POST /candidates/{id}/evaluate` - Sin verificación de asignación
- ❌ `POST /jobs/{id}/close` - Solo verifica que sea consultor, no owner

#### Recomendación:
```python
# Agregar middleware de ownership
async def require_job_owner(job_id: str, current_user: User):
    job = await job_service.get_by_id(job_id)
    if not job:
        raise HTTPException(404)
    if current_user.role != UserRole.SUPER_ADMIN:
        if str(job.assigned_consultant_id) != str(current_user.id):
            raise HTTPException(403, "No eres el owner de este job")
```

---

## 4. RATE LIMITS + WAF + MFA PARA ADMIN

### 4.1 Rate limiting implementado
**Estado:** ✅ **CUMPLE**

#### Implementación:
```python
# backend/app/core/rate_limit.py
- RateLimitMiddleware con Redis
- Límites por endpoint:
  - Login: 3 por minuto
  - Auth: 5 por minuto
  - Usuario autenticado: 100 por minuto
  - General: 60 por minuto
- Protección contra enumeration attacks
- Bloqueo de IPs sospechosas
```

#### Auth endpoints con rate limiting:
```python
# backend/app/api/auth.py
@router.post("/login")
@limiter.limit("5/minute")  # ✅

@router.post("/register")
@limiter.limit("5/minute")  # ✅

@router.post("/refresh")
@limiter.limit("5/minute")  # ✅
```

### 4.2 WAF configurado
**Estado:** ❌ **NO CUMPLE**

#### Falta:
- ❌ No hay WAF configurado (ModSecurity, AWS WAF, Cloudflare)
- ❌ No hay protección contra:
  - SQL Injection (aunque SQLAlchemy parametriza)
  - XSS (no hay headers de seguridad configurados)
  - CSRF (no hay protección CSRF visible)
  - Path traversal

#### Headers de seguridad faltantes:
```python
# Agregar middleware:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000; includeSubDomains
- Content-Security-Policy
```

### 4.3 MFA obligatorio para admin
**Estado:** ❌ **NO CUMPLE**

#### Falta:
- ❌ No hay implementación de MFA/TOTP
- ❌ No hay forzado MFA para admin
- ❌ No hay opción de MFA para usuarios

#### Recomendación:
```python
# Implementar con pyotp
import pyotp

# Para admin login
if user.role == UserRole.SUPER_ADMIN and not verify_totp(user, totp_code):
    raise HTTPException(403, "MFA requerido para admin")
```

---

## 5. DEPENDENCIAS AL DÍA + ESCANEO AUTOMÁTICO

### 5.1 requirements.txt - librerías actualizadas
**Estado:** ⚠️ **PARCIAL**

#### Dependencias con versiones fijas (bueno):
```txt
fastapi==0.109.0
sqlalchemy==2.0.25
pydantic==2.5.3
```

#### Problemas:
- ⚠️ Algunas dependencias podrían tener vulnerabilidades conocidas
- ❌ No hay archivo `requirements-dev.txt` separado
- ❌ No hay `Pipfile.lock` o `poetry.lock` para reproducibilidad

#### Vulnerabilidades conocidas potenciales (requiere escaneo):
```bash
# Ejecutar:
pip install safety
safety check -r backend/requirements.txt
```

### 5.2 package.json - dependencias sin vulnerabilidades
**Estado:** ⚠️ **PARCIAL**

#### Frontend dependencies:
```json
{
  "next": "14.1.0",      # ⚠️ Verificar versiones
  "react": "^18.2.0",
  "axios": "^1.6.5"       # ⚠️ Axios tuvo CVEs recientes
}
```

#### Falta:
- ❌ No hay `package-lock.json` en el repositorio
- ❌ No se ejecuta `npm audit` en CI/CD

### 5.3 Escaneo automático en CI/CD
**Estado:** ❌ **NO CUMPLE**

#### Falta completamente:
- ❌ No hay `.github/workflows/` configurados
- ❌ No hay escaneo SAST (Semgrep, CodeQL, SonarCloud)
- ❌ No hay escaneo de dependencias (Dependabot, Snyk)
- ❌ No hay escaneo de secretos (GitLeaks, truffleHog)

#### Workflow recomendado:
```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Secret Detection
        uses: trufflesecurity/trufflehog@main
      - name: Dependency Check
        uses: snyk/actions/python@master
      - name: SAST
        uses: returntocorp/semgrep-action@v1
```

---

## 6. OBSERVABILIDAD + ALERTAS + PLAN DE INCIDENTES

### 6.1 Logs configurados
**Estado:** ✅ **CUMPLE**

#### Implementado:
```python
# backend/app/core/security_logging.py
- SecurityLogger con eventos:
  - login_attempt (success/failure)
  - logout
  - unauthorized_access
  - password_change
  - user_modification
  - config_change
  - suspicious_activity
  - rate_limit_hit
  - token_refresh

# Formato JSON estructurado
# Incluye IP, user-agent, timestamp, user_id
```

#### Stack de observabilidad:
```yaml
# docker-compose.yml tiene:
- Prometheus (métricas)
- Grafana (dashboards)
- Loki (logs)
- Alertmanager (alertas)
- Promtail (log shipping)
```

### 6.2 Alertas activas
**Estado:** ✅ **CUMPLE**

#### Implementado:
```python
# backend/app/core/alerts.py
- AlertManager con reglas:
  - high_error_rate (>5%)
  - high_latency_p95 (>2s)
  - high_db_connections (>80%)
  - high_llm_error_rate (>10%)
  - high_disk_usage (>85%)
  - high_memory_usage (>90%)

# Notificadores:
- Console notifier
- Webhook notifier
- Slack notifier
```

### 6.3 Plan de respuesta a incidentes documentado
**Estado:** ❌ **NO CUMPLE**

#### Falta:
- ❌ No hay documento INCIDENT_RESPONSE.md
- ❌ No hay runbooks para:
  - Breach de seguridad
  - Ransomware
  - DDoS
  - Data exfiltration
  - Compromiso de credenciales
- ❌ No hay contactos de emergencia
- ❌ No hay definición de severidad (P1/P2/P3/P4)
- ❌ No hay procedimientos de escalación

#### Template necesario:
```markdown
# INCIDENT_RESPONSE.md
1. Detección -> Slack #security-alerts
2. Contención -> Isolate affected systems
3. Eradicación -> Remove threat
4. Recuperación -> Restore from backups
5. Lecciones aprendidas -> Post-mortem
```

---

## 7. BACKUPS PROBADOS (RESTORE)

### 7.1 Backups automáticos
**Estado:** ❌ **NO CUMPLE**

#### Falta:
- ❌ No hay servicio de backup en docker-compose.yml
- ❌ No hay scripts de backup automatizado
- ❌ No hay política de retención (3-2-1 rule)

#### Documentación existe pero no implementación:
```bash
# DB_SECURITY_PERFORMANCE_REPORT.md menciona:
# Pero no hay scripts reales en el repo

# Falta:
- scripts/backup.sh
- scripts/restore.sh
- Cron job para backups automáticos
```

### 7.2 Pruebas de restore periódicas
**Estado:** ❌ **NO CUMPLE**

#### Falta:
- ❌ No hay pruebas automatizadas de restore
- ❌ No hay documentación de DR (Disaster Recovery)
- ❌ No hay RTO/RPO definidos
- ❌ No hay ambiente de staging para probar restores

#### Solución requerida:
```yaml
# Agregar a docker-compose.yml
pg_backup:
  image: postgres:15-alpine
  volumes:
    - ./backups:/backups
    - ./scripts/backup.sh:/backup.sh:ro
  command: >
    sh -c "echo '0 2 * * * /backup.sh' | crontab - && crond -f"
```

```bash
# scripts/backup.sh
#!/bin/bash
set -e
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/backups/ats_backup_${TIMESTAMP}.sql.gz"

pg_dump -h postgres -U postgres ats_platform | gzip > ${BACKUP_FILE}

# Retención: 30 días
find /backups -name "ats_backup_*.sql.gz" -mtime +30 -delete
```

---

## 🚨 PLAN URGENTE PARA ITEMS CON ❌

### Prioridad CRÍTICA (Resolver en 24-48h):

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. ROTAR SECRET_KEY INMEDIATAMENTE                              │
│    - Invalidará todas las sesiones activas                      │
│    - Usar: python scripts/generate_secrets.py                   │
│    - Mover a variable de entorno                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. ELIMINAR/CAMBIAR backend/.env DEL REPOSITORIO                │
│    - git rm --cached backend/.env                               │
│    - Agregar a .gitignore                                       │
│    - Rotar DEFAULT_ADMIN_PASSWORD                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 3. CREAR USUARIOS DB CON MÍNIMO PRIVILEGIO                      │
│    - Crear ats_backend, ats_worker                              │
│    - Revocar permisos de postgres                               │
│    - Actualizar DATABASE_URL                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 4. IMPLEMENTAR BACKUPS AUTOMÁTICOS                              │
│    - Crear scripts/backup.sh                                    │
│    - Configurar cron en docker-compose                          │
│    - Probar restore en ambiente de staging                      │
└─────────────────────────────────────────────────────────────────┘
```

### Prioridad ALTA (Resolver en 1 semana):

```
┌─────────────────────────────────────────────────────────────────┐
│ 5. IMPLEMENTAR CI/CD CON ESCANEO DE SEGURIDAD                   │
│    - GitHub Actions workflow                                    │
│    - Secret detection (truffleHog)                              │
│    - Dependency scanning (Snyk/Safety)                          │
│    - SAST (Semgrep/CodeQL)                                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 6. FIX IDOR - AGREGAR VERIFICACIÓN DE OWNERSHIP                 │
│    - Middleware para verificar ownership de jobs                │
│    - Middleware para verificar ownership de candidates          │
│    - Auditar todos los endpoints                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 7. IMPLEMENTAR MFA PARA ADMIN                                   │
│    - Usar pyotp para TOTP                                       │
│    - Forzar MFA para super_admin                                │
│    - UI para configurar MFA                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Prioridad MEDIA (Resolver en 2 semanas):

```
┌─────────────────────────────────────────────────────────────────┐
│ 8. IMPLEMENTAR WAF/PROTECCIÓN ADICIONAL                         │
│    - Headers de seguridad (HSTS, CSP, etc.)                     │
│    - Rate limiting en capa de edge (Cloudflare)                 │
│    - Input validation reforzada                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 9. CREAR PLAN DE RESPUESTA A INCIDENTES                         │
│    - Documento INCIDENT_RESPONSE.md                             │
│    - Runbooks para escenarios comunes                           │
│    - Contactos de emergencia                                    │
│    - Definición de RTO/RPO                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 CHECKLIST FINAL

| # | Item | Estado | Prioridad |
|---|------|--------|-----------|
| 1.1 | Escaneo de secretos en repositorio | ❌ | 🔴 CRÍTICO |
| 1.2 | API keys, passwords, tokens hardcodeados | ❌ | 🔴 CRÍTICO |
| 2.1 | Permisos mínimos en DB | ❌ | 🔴 CRÍTICO |
| 2.2 | Credenciales cloud restrictivas | ❌ | 🟠 ALTO |
| 2.3 | Usuarios sistema limitados | ⚠️ | 🟡 MEDIO |
| 3.1 | Validación IDOR - usuario A ve B | ⚠️ | 🟠 ALTO |
| 3.2 | Verificación ownership endpoints | ⚠️ | 🟠 ALTO |
| 4.1 | Rate limiting implementado | ✅ | - |
| 4.2 | WAF configurado | ❌ | 🟠 ALTO |
| 4.3 | MFA obligatorio para admin | ❌ | 🔴 CRÍTICO |
| 5.1 | requirements.txt actualizado | ⚠️ | 🟡 MEDIO |
| 5.2 | package.json sin vulnerabilidades | ⚠️ | 🟡 MEDIO |
| 5.3 | Escaneo automático en CI/CD | ❌ | 🔴 CRÍTICO |
| 6.1 | Logs configurados | ✅ | - |
| 6.2 | Alertas activas | ✅ | - |
| 6.3 | Plan de respuesta documentado | ❌ | 🟠 ALTO |
| 7.1 | Backups automáticos | ❌ | 🔴 CRÍTICO |
| 7.2 | Pruebas de restore periódicas | ❌ | 🔴 CRÍTICO |

**Total: 5 ✅ | 9 ❌ | 4 ⚠️**

---

## 🎯 PRÓXIMOS PASOS INMEDIATOS

```bash
# Ejecutar AHORA (en orden):

# 1. Rotar SECRET_KEY
cd /home/andres/.openclaw/workspace/ats-platform
python scripts/generate_secrets.py

# 2. Eliminar .env del repo
git rm --cached backend/.env
echo "backend/.env" >> .gitignore

# 3. Crear usuarios DB con mínimo privilegio
# (Ver scripts en DB_SECURITY_PERFORMANCE_REPORT.md)

# 4. Configurar backups
# (Ver sección 7.1 de este documento)

# 5. Crear GitHub Actions workflow
# (Ver sección 5.3 de este documento)
```

---

**Reporte generado por:** Subagent de Seguridad  
**Fecha:** 2026-02-17  
**Próxima revisión recomendada:** Después de completar items CRÍTICOS
