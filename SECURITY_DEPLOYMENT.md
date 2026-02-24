# 🔒 Database Security Fixes - Quick Deployment Guide

Guía rápida para desplegar los fixes críticos de seguridad de base de datos.

## 🚀 Pasos de Despliegue

### 1. Configurar Variables de Entorno

Edita el archivo `.env` o configura las variables de entorno:

```bash
# PostgreSQL (contraseñas seguras - mínimo 16 caracteres)
POSTGRES_PASSWORD=YourSecurePostgresPassword123!

# Usuarios de aplicación
ATS_APP_PASSWORD=YourSecureAppPassword456!
ATS_MIGRATOR_PASSWORD=YourSecureMigratorPassword789!
ATS_READONLY_PASSWORD=YourSecureReadonlyPassword012!

# Encriptación (generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-32-byte-base64-encoded-fernet-key-here

# JWT Secret
SECRET_KEY=your-super-secret-jwt-key-min-32-chars
```

### 2. Generar Certificados SSL

```bash
cd ats-platform
./scripts/generate_ssl_certs.sh
```

Esto creará los certificados en `./ssl/`:
- `ca.crt` - Certificado de la Autoridad Certificadora
- `server.crt` - Certificado del servidor PostgreSQL
- `server.key` - Clave privada del servidor

### 3. Copiar Certificados al Volumen

```bash
# Crear directorio de backups
mkdir -p backups

# Copiar certificados (después de iniciar postgres)
docker-compose up -d postgres
docker cp ssl/server.crt ats_postgres:/var/lib/postgresql/ssl/
docker cp ssl/server.key ats_postgres:/var/lib/postgresql/ssl/
docker cp ssl/ca.crt ats_postgres:/var/lib/postgresql/ssl/
docker-compose restart postgres
```

### 4. Crear Usuarios de Base de Datos

```bash
# Esperar a que PostgreSQL esté listo
docker-compose exec postgres pg_isready -U postgres

# Ejecutar script de creación de usuarios
docker-compose exec -T postgres psql -U postgres -d ats_platform < scripts/create_db_users.sql

# Verificar usuarios creados
docker-compose exec postgres psql -U postgres -c "\du"
```

### 5. Ejecutar Migraciones

```bash
# Ejecutar migración de seguridad
docker-compose exec backend alembic upgrade security_hardening_001
```

### 6. Iniciar Todos los Servicios

```bash
docker-compose up -d
```

### 7. Verificar Instalación

```bash
# Verificar SSL
docker-compose exec postgres psql "sslmode=require" -U ats_app -d ats_platform -c "SHOW ssl;"

# Verificar auditoría
docker-compose exec postgres psql -U ats_app -d ats_platform -c "SELECT * FROM hh_audit_log LIMIT 5;"

# Verificar encriptación (crear candidato de prueba)
curl -X POST http://localhost:8000/api/v1/candidates \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test","email":"test@example.com","phone":"+1234567890"}'

# Verificar en base de datos (debe aparecer encriptado)
docker-compose exec postgres psql -U postgres -d ats_platform -c "SELECT email FROM hh_candidates WHERE full_name='Test';"
```

## 📋 Verificación de Seguridad

### Checklist de Seguridad

- [ ] Variables de entorno configuradas con contraseñas seguras
- [ ] Certificados SSL generados y copiados
- [ ] Usuarios de BD creados con mínimo privilegio
- [ ] Migraciones de seguridad ejecutadas
- [ ] Encriptación PII funcionando (verificar en BD)
- [ ] Auditoría funcionando (insertar registro y verificar hh_audit_log)
- [ ] Backups configurados (verificar cron en servicio backup)
- [ ] SSL requerido en todas las conexiones

### Comandos de Verificación Rápida

```bash
# 1. SSL habilitado
docker-compose exec postgres psql -U postgres -c "SHOW ssl;"
# Debe retornar: on

# 2. Usuarios correctos
docker-compose exec postgres psql -U postgres -c "\du"
# Deben aparecer: ats_app, ats_migrator, ats_readonly

# 3. Conexión con ats_app (debe funcionar)
docker-compose exec postgres psql "sslmode=require" -U ats_app -d ats_platform -c "SELECT 1;"

# 4. ats_app NO puede hacer DROP (debe fallar)
docker-compose exec postgres psql -U ats_app -d ats_platform -c "DROP TABLE hh_candidates;"
# Debe retornar: ERROR: permission denied

# 5. Backup funciona
./scripts/backup.sh
# Debe crear archivo en backups/

# 6. Auditoría activa
docker-compose exec postgres psql -U postgres -d ats_platform -c "SELECT COUNT(*) FROM hh_audit_log;"
```

## 🆘 Troubleshooting

### "permission denied for schema public"

```bash
# Ejecutar como postgres superuser
docker-compose exec postgres psql -U postgres -d ats_platform -c "GRANT USAGE ON SCHEMA public TO ats_app;"
```

### "sslmode=require but server doesn't support SSL"

```bash
# Regenerar certificados
./scripts/generate_ssl_certs.sh
docker-compose restart postgres
```

### "Failed to decrypt value"

Verificar que `ENCRYPTION_KEY` es la misma usada para encriptar los datos.

### "Fernet key must be 32 url-safe base64-encoded bytes"

```bash
# Generar clave válida
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 🔐 Notas de Seguridad

1. **NUNCA** subir el archivo `.env` al repositorio
2. **NUNCA** subir certificados SSL (`ssl/`)
3. **NUNCA** subir backups (`backups/`)
4. Guardar `ENCRYPTION_KEY` en un gestor de secretos (Vault, AWS Secrets Manager)
5. Rotar contraseñas cada 90 días
6. Revisar logs de auditoría regularmente

## 📚 Documentación Completa

Ver `docs/SECURITY_DB.md` para documentación detallada.

## ⚠️ Importante

- Los datos PII existentes se mantienen en texto plano hasta que se actualicen
- Los datos nuevos se encriptan automáticamente
- La migración es segura y no elimina datos existentes
