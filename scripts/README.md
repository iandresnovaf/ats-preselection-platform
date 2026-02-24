# Scripts de Automatización para Producción - ATS Platform

Este directorio contiene scripts de automatización para el despliegue y mantenimiento de ATS Platform en producción.

## 📋 Scripts Disponibles

### 1. `pre_deploy_check.py` - Verificación Pre-Deploy

Verifica que todo esté configurado correctamente antes de un deploy a producción.

**Verificaciones incluidas:**
- ✅ Archivos `.env` no trackeados por git
- ✅ No hay valores placeholder (CHANGE_ME_, REPLACE_WITH_, etc.)
- ✅ Variables críticas configuradas (SECRET_KEY, DATABASE_URL, etc.)
- ✅ Conectividad a base de datos PostgreSQL
- ✅ Conectividad a Redis
- ✅ Dependencias instaladas
- ✅ Docker disponible
- ✅ Certificados SSL
- ✅ Espacio en disco

**Uso:**
```bash
# Verificación estándar
python scripts/pre_deploy_check.py

# Modo estricto (falla también con warnings)
python scripts/pre_deploy_check.py --strict

# Omitir verificaciones de DB
python scripts/pre_deploy_check.py --skip-db

# Output silencioso (solo retorna código de salida)
python scripts/pre_deploy_check.py --quiet
```

**Códigos de salida:**
- `0` - Todo OK, listo para deploy
- `1` - Errores o warnings encontrados

---

### 2. `deploy_production.sh` - Deploy Automatizado

Pipeline completo de deploy a producción con rollback automático.

**Flujo del deploy:**
1. Pre-deploy checks
2. Backup de seguridad
3. Tests de seguridad (bandit, safety, semgrep)
4. Build de imágenes Docker
5. Migraciones de base de datos (Alembic)
6. Deploy de servicios
7. Health check
8. Rollback automático si falla
9. Limpieza de imágenes antiguas

**Uso:**
```bash
# Deploy con versión automática (timestamp-gitsha)
./scripts/deploy_production.sh

# Deploy con versión específica
./scripts/deploy_production.sh v1.2.3

# Deploy forzado sin confirmación
./scripts/deploy_production.sh --force

# Simular deploy (sin cambios reales)
./scripts/deploy_production.sh --dry-run

# Skip tests de seguridad
./scripts/deploy_production.sh --skip-tests

# Deshabilitar rollback automático
./scripts/deploy_production.sh --no-rollback
```

**Variables de entorno:**
```bash
VERSION=v2.0.0 ./scripts/deploy_production.sh
```

---

### 3. `verify_deployment.sh` - Verificación Post-Deploy

Verifica que el deployment esté funcionando correctamente.

**Verificaciones incluidas:**
- ✅ Endpoint `/health` responde HTTP 200
- ✅ Endpoint `/metrics` accesible (Prometheus)
- ✅ Headers de seguridad presentes
- ✅ No hay secretos expuestos en respuestas
- ✅ Conectividad a PostgreSQL
- ✅ Conectividad a Redis
- ✅ Certificado SSL válido
- ✅ Tiempos de respuesta aceptables
- ✅ Contenedores Docker saludables

**Uso:**
```bash
# Verificación local
./scripts/verify_deployment.sh

# Verificar endpoint remoto
./scripts/verify_deployment.sh --endpoint https://api.example.com

# Output en formato JSON
./scripts/verify_deployment.sh --json

# Verbose con reporte
./scripts/verify_deployment.sh --verbose --report /tmp/verify_report.txt
```

**Códigos de salida:**
- `0` - Deployment verificado exitosamente
- `1` - Se encontraron problemas

---

### 4. `emergency_rollback.sh` - Rollback de Emergencia

⚠️ **USAR SOLO EN SITUACIONES DE EMERGENCIA**

Script para rollback rápido a versión anterior.

**Capacidades:**
- Rollback a versión anterior de Docker
- Restauración de base de datos desde backup
- Notificación al equipo
- Backup de seguridad antes del rollback
- Verificación post-rollback

**⚠️ Precauciones:**
- Siempre crea un backup antes de restaurar DB
- Requiere confirmación interactiva (a menos que use `--force`)
- Puede causar downtime temporal
- La restauración de DB puede causar pérdida de datos recientes

**Uso:**
```bash
# Rollback a versión anterior (interactivo)
./scripts/emergency_rollback.sh

# Rollback con restauración de DB
./scripts/emergency_rollback.sh --restore-db --force

# Rollback a versión específica
./scripts/emergency_rollback.sh --version v1.2.0

# Rollback con notificación
./scripts/emergency_rollback.sh --notify --reason "Critical bug in v1.3.0"

# Usar backup específico
./scripts/emergency_rollback.sh --restore-db --backup /path/to/backup.sql
```

---

## 🔧 Requisitos

### Python Scripts
- Python 3.8+
- `asyncpg` (para verificación de DB)
- `redis` (para verificación de Redis)
- `jq` (para procesamiento JSON en bash scripts)

### Bash Scripts
- Bash 4.0+
- Docker 20.10+
- Docker Compose 2.0+
- curl
- openssl (para verificación SSL)

### Opcionales (para tests de seguridad)
```bash
pip install bandit safety semgrep
```

---

## 📁 Estructura de Logs

Los scripts generan logs en el directorio `logs/`:

```
logs/
├── deploy_20240217_143022.log
├── deploy_20240217_153045.log
├── rollback_20240217_160012.log
└── bandit_20240217_143025.json
```

---

## 🔄 Flujo de Deploy Recomendado

```bash
# 1. Verificar pre-condiciones
python scripts/pre_deploy_check.py --strict

# 2. Ejecutar deploy
./scripts/deploy_production.sh v1.2.3

# 3. Verificar deployment
./scripts/verify_deployment.sh --verbose

# En caso de emergencia:
# ./scripts/emergency_rollback.sh --restore-db
```

---

## 🚨 Alertas y Notificaciones

Para habilitar notificaciones, configurar variables de entorno:

```bash
# Slack
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"

# Discord
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/XXX/YYY"

# Email (requiere mail configurado)
export ALERT_EMAIL="ops-team@example.com"
```

---

## 📝 Checklist de Seguridad

- [ ] Todos los scripts tienen permisos de ejecución
- [ ] Los scripts no contienen secretos hardcodeados
- [ ] Los logs no registran información sensible
- [ ] Los backups se almacenan en ubicación segura
- [ ] El webhook de notificaciones usa HTTPS

---

## 🔍 Troubleshooting

### Pre-deploy check falla
```bash
# Ver detalles del error
python scripts/pre_deploy_check.py --verbose

# Verificar variables de entorno
cat backend/.env | grep -v PASSWORD | grep -v SECRET
```

### Deploy falla durante migraciones
```bash
# Ver logs de migración
docker compose logs backend | grep alembic

# Verificar estado de migraciones
docker compose exec backend alembic current
docker compose exec backend alembic history
```

### Rollback no funciona
```bash
# Verificar imágenes disponibles
docker images ats-backend

# Verificar backups disponibles
ls -la backups/*.sql
```

---

## 📚 Referencias

- [Docker Compose](https://docs.docker.com/compose/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)
- [Bandit Security Linter](https://bandit.readthedocs.io/)
- [Safety Check](https://pyup.io/safety/)
