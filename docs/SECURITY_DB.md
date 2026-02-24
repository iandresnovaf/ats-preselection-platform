# 🔒 Database Security Hardening Guide

Guía de endurecimiento de seguridad de base de datos para ATS Platform.

## 📋 Cambios Implementados

### 1. Usuarios de BD con Mínimo Privilegio

Se han creado 3 usuarios de base de datos con principio de mínimo privilegio:

| Usuario | Privilegios | Uso |
|---------|-------------|-----|
| `ats_app` | SELECT, INSERT, UPDATE, DELETE | Aplicación principal |
| `ats_migrator` | DDL completo (CREATE, ALTER, DROP) | Migraciones Alembic |
| `ats_readonly` | SELECT únicamente | Reportes y análisis |

**Archivos:**
- `scripts/create_db_users.sql` - Script de creación de usuarios
- `docker-compose.yml` - Configuración actualizada

**Uso:**
```bash
# Ejecutar como superusuario postgres
psql -U postgres -d ats_platform -f scripts/create_db_users.sql
```

### 2. SSL/TLS para Conexiones DB

Todas las conexiones a PostgreSQL requieren SSL/TLS:

**Configuración en `docker-compose.yml`:**
```yaml
postgres:
  environment:
    POSTGRES_SSL_MODE: require
  command:
    - "postgres"
    - "-c"
    - "ssl=on"
    - "-c"
    - "ssl_cert_file=/var/lib/postgresql/ssl/server.crt"
    - "-c"
    - "ssl_key_file=/var/lib/postgresql/ssl/server.key"
```

**Generar certificados:**
```bash
./scripts/generate_ssl_certs.sh
```

**URL de conexión (backend):**
```
DATABASE_URL=postgresql+asyncpg://ats_app:password@postgres:5432/ats_platform?ssl=require
```

### 3. Backups Automáticos

Servicio de backup automatizado con cron job:

**Ejecución manual:**
```bash
./scripts/backup.sh
```

**Restaurar backup:**
```bash
# Listar backups disponibles
./scripts/restore.sh -l

# Restaurar backup específico
./scripts/restore.sh backup_ats_platform_20240115_120000.dump

# Modo test (verificar sin restaurar)
./scripts/restore.sh -t backup_ats_platform_20240115_120000.dump
```

**Configuración en `docker-compose.yml`:**
```yaml
backup:
  image: postgres:15-alpine
  command: >
    sh -c "
      apk add --no-cache postgresql15-client &&
      echo '0 2 * * * /usr/local/bin/backup.sh' | crontab - &&
      crond -f -l 2
    "
```

Los backups se ejecutan diariamente a las 2:00 AM y se retienen por 30 días.

### 4. Cifrado de Datos PII

Los siguientes campos de `HHCandidate` están encriptados en reposo:

- `email` - Correo electrónico
- `phone` - Teléfono
- `national_id` - Documento de identidad

**Tecnología:** Fernet (AES-128 en modo CBC con PKCS7 padding)

**Implementación:**
```python
# app/core/database.py
class EncryptedType(TypeDecorator):
    """Tipo de columna SQLAlchemy que encripta/desencripta automáticamente."""
    
    def process_bind_param(self, value, dialect):
        # Encriptar antes de guardar
        return encryption_manager.encrypt(str(value))
    
    def process_result_value(self, value, dialect):
        # Desencriptar al leer
        return encryption_manager.decrypt(str(value))
```

**Configuración:**
```bash
# Generar clave de encriptación
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Agregar a .env
ENCRYPTION_KEY=your-generated-key-here
```

⚠️ **IMPORTANTE:** Si se pierde la `ENCRYPTION_KEY`, los datos PII encriptados no podrán ser recuperados.

### 5. Auditoría de DB

Sistema de auditoría que registra automáticamente cambios en tablas críticas:

**Tablas auditadas:**
- `HHCandidate`
- `HHClient`
- `HHRole`
- `HHApplication`
- `HHDocument`
- `User`

**Estructura de tabla `hh_audit_log`:**
```sql
CREATE TABLE hh_audit_log (
    audit_id UUID PRIMARY KEY,
    entity_type TEXT NOT NULL,     -- 'HHCandidate', 'HHApplication', etc.
    entity_id UUID NOT NULL,       -- ID del registro modificado
    action TEXT NOT NULL,          -- 'create', 'update', 'delete'
    changed_by TEXT,               -- Usuario que realizó el cambio
    changed_at TIMESTAMP,          -- Fecha/hora del cambio
    diff_json JSONB                -- Diferencias (old/new values)
);
```

**Consultar logs:**
```python
from app.core.audit import get_audit_logs

# Obtener logs de un candidato específico
logs = get_audit_logs(
    db=session,
    entity_type='HHCandidate',
    entity_id='uuid-del-candidato',
    limit=50
)
```

## 🚀 Instrucciones de Despliegue

### Paso 1: Configurar Variables de Entorno

```bash
# .env o docker-compose.override.yml
POSTGRES_PASSWORD=your-secure-postgres-password
ATS_APP_PASSWORD=your-secure-app-password
ATS_MIGRATOR_PASSWORD=your-secure-migrator-password
ATS_READONLY_PASSWORD=your-secure-readonly-password
ENCRYPTION_KEY=your-fernet-encryption-key
SECRET_KEY=your-jwt-secret-key
```

### Paso 2: Generar Certificados SSL

```bash
cd ats-platform
./scripts/generate_ssl_certs.sh
```

### Paso 3: Crear Usuarios de BD

```bash
# Iniciar solo PostgreSQL primero
docker-compose up -d postgres

# Esperar a que esté listo
docker-compose exec postgres pg_isready -U postgres

# Crear usuarios
docker-compose exec -T postgres psql -U postgres -d ats_platform < scripts/create_db_users.sql
```

### Paso 4: Ejecutar Migraciones

```bash
# Usar usuario migrator para DDL
docker-compose exec backend alembic upgrade head
```

### Paso 5: Iniciar Todos los Servicios

```bash
docker-compose up -d
```

## 🔍 Verificación de Seguridad

### Verificar SSL/TLS

```bash
# Conectarse con SSL obligatorio
docker-compose exec postgres psql "sslmode=require" -U ats_app -d ats_platform -c "SHOW ssl;"

# Debe retornar: ssl = on
```

### Verificar Encriptación PII

```python
# En Python shell
from app.models.core_ats import HHCandidate
from app.core.database import async_session_maker

async def test_encryption():
    async with async_session_maker() as session:
        # Crear candidato
        candidate = HHCandidate(
            full_name="Test User",
            email="test@example.com",
            phone="+573001234567",
            national_id="1234567890"
        )
        session.add(candidate)
        await session.commit()
        
        # Verificar en BD directamente (debe estar encriptado)
        result = await session.execute(
            "SELECT email, phone FROM hh_candidates WHERE candidate_id = :id",
            {"id": candidate.candidate_id}
        )
        row = result.fetchone()
        print(f"Email en BD: {row.email}")  # Debe verse encriptado
        print(f"Teléfono en BD: {row.phone}")  # Debe verse encriptado
        
        # Leer a través del modelo (debe verse desencriptado)
        print(f"Email desencriptado: {candidate.email}")
        print(f"Teléfono desencriptado: {candidate.phone}")
```

### Verificar Auditoría

```sql
-- Ver logs de auditoría
SELECT * FROM hh_audit_log 
ORDER BY changed_at DESC 
LIMIT 10;

-- Ver cambios de un candidato específico
SELECT * FROM hh_audit_log 
WHERE entity_type = 'HHCandidate' 
  AND entity_id = 'uuid-del-candidato'
ORDER BY changed_at DESC;
```

### Verificar Permisos de Usuarios

```sql
-- Conectarse como ats_app (solo debe poder SELECT, INSERT, UPDATE, DELETE)
\c ats_platform ats_app

-- Esto debería FALLAR:
CREATE TABLE test_table (id INT);  -- ERROR: permission denied
DROP TABLE hh_candidates;          -- ERROR: permission denied

-- Esto debería FUNCIONAR:
SELECT * FROM hh_candidates LIMIT 1;
INSERT INTO hh_candidates (full_name) VALUES ('Test');
```

## ⚠️ Notas Importantes

### Migración de Datos Existentes

Los datos PII existentes se mantienen en texto plano hasta que se actualicen:

```python
# Script para migrar datos existentes a encriptados
async def migrate_existing_pii():
    async with async_session_maker() as session:
        result = await session.execute(
            "SELECT candidate_id FROM hh_candidates WHERE pii_encrypted = FALSE"
        )
        for row in result:
            candidate = await session.get(HHCandidate, row.candidate_id)
            # Simplemente tocar el registro lo encripta
            candidate.pii_encrypted = True
        await session.commit()
```

### Backup de la Clave de Encriptación

La `ENCRYPTION_KEY` es crítica. Guárdala en:

- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- GCP Secret Manager

**NUNCA** la incluyas en el repositorio de código.

### Rotación de Contraseñas

Las contraseñas de usuarios de BD deben rotarse cada 90 días:

```sql
-- Rotar contraseña
ALTER USER ats_app WITH PASSWORD 'new_secure_password';
ALTER USER ats_migrator WITH PASSWORD 'new_secure_password';
ALTER USER ats_readonly WITH PASSWORD 'new_secure_password';
```

## 📚 Referencias

- [PostgreSQL SSL Documentation](https://www.postgresql.org/docs/current/ssl-tcp.html)
- [Fernet Encryption](https://cryptography.io/en/latest/fernet/)
- [SQLAlchemy Type Decorators](https://docs.sqlalchemy.org/en/20/core/custom_types.html#sqlalchemy.types.TypeDecorator)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)

## 🆘 Troubleshooting

### Error: "sslmode=require" pero PostgreSQL no tiene SSL

```bash
# Verificar que SSL esté habilitado
docker-compose exec postgres psql -U postgres -c "SHOW ssl;"

# Si retorna 'off', regenerar certificados:
./scripts/generate_ssl_certs.sh
docker-compose restart postgres
```

### Error: "permission denied for table"

```bash
# Verificar que los usuarios estén creados
docker-compose exec postgres psql -U postgres -c "\du"

# Re-crear usuarios si es necesario
docker-compose exec -T postgres psql -U postgres < scripts/create_db_users.sql
```

### Error: "Failed to decrypt value"

```bash
# Verificar que ENCRYPTION_KEY esté configurada
echo $ENCRYPTION_KEY

# Si es diferente a la usada para encriptar los datos, 
# los datos están perdidos (a menos que tengas backup de la clave)
```

### Error: "Invalid Fernet key"

```bash
# Generar nueva clave válida
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# La nueva clave solo funcionará para datos NUEVOS
# Los datos antiguos encriptados con otra clave no se podrán leer
```
