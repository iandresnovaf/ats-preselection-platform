# Guía de Seguridad y Gestión de Secretos

> **IMPORTANTE**: Esta guía describe cómo gestionar secretos y configuración sensible de forma segura en el ATS Platform.

## Tabla de Contenidos

- [Resumen Rápido](#resumen-rápido)
- [Configuración Inicial](#configuración-inicial)
- [Rotación de Secretos](#rotación-de-secretos)
- [Variables de Entorno](#variables-de-entorno)
- [Buenas Prácticas](#buenas-prácticas)
- [Chequeo de Seguridad](#chequeo-de-seguridad)
- [Respuesta a Incidentes](#respuesta-a-incidentes)

---

## Resumen Rápido

```bash
# 1. Setup inicial de secretos
python scripts/setup_secrets.py

# 2. Crear usuario admin (interactivo)
cd backend && python create_admin.py

# 3. Validar configuración
python scripts/setup_secrets.py --check
```

---

## Configuración Inicial

### Paso 1: Generar Secretos

El script `setup_secrets.py` automatiza la configuración inicial segura:

```bash
python scripts/setup_secrets.py
```

Este script:
- ✅ Genera SECRET_KEY criptográficamente seguro (64 caracteres)
- ✅ Genera ENCRYPTION_KEY para Fernet
- ✅ Genera contraseña segura para admin (24 caracteres)
- ✅ Crea `backend/.env` a partir de `.env.example`
- ✅ Establece permisos restrictivos (600) en el archivo
- ✅ Valida que `.env` no esté trackeado por git

### Paso 2: Personalizar Configuración

Después de ejecutar el setup, edita `backend/.env`:

```bash
# Database - Actualizar con tus credenciales reales
DATABASE_URL=postgresql+asyncpg://usuario:TU_PASSWORD_REAL@localhost:5432/ats_platform

# Admin - Cambiar email si es necesario
DEFAULT_ADMIN_EMAIL=admin@tuempresa.com

# API Keys
OPENAI_API_KEY=sk-tu-api-key-real

# WhatsApp (opcional)
WHATSAPP_ACCESS_TOKEN=tu-token-real
```

### Paso 3: Crear Admin

**Opción A: Modo interactivo (recomendado)**
```bash
cd backend
python create_admin.py
# Solicitará contraseña de forma segura (sin mostrar en pantalla)
```

**Opción B: Generar contraseña aleatoria**
```bash
cd backend
python create_admin.py --generate
# Muestra la contraseña generada UNA SOLA VEZ
```

**⚠️ NUNCA usar:**
```bash
# NO hagas esto - la contraseña queda en el history
python create_admin.py --password "mi_password"
```

---

## Rotación de Secretos

### ¿Cuándo Rotar?

- **Inmediatamente**: Si sospechas que un secreto fue comprometido
- **Cada 90 días**: SECRET_KEY, ENCRYPTION_KEY
- **Después de rotación de personal**: Cuando alguien con acceso sale
- **Después de un incidente**: Breach de seguridad detectado

### Proceso de Rotación

#### 1. SECRET_KEY (Tokens JWT)

```bash
# Generar nuevo SECRET_KEY
python scripts/generate_secrets.py --output .env.new

# Hacer backup del .env actual
cp backend/.env backend/.env.backup.$(date +%Y%m%d)

# Actualizar SECRET_KEY (manteniendo otras variables)
# Editar manualmente o usar:
python scripts/setup_secrets.py --force

# Reiniciar aplicación
# Los tokens existentes quedarán inválidos (usuarios deben loguearse de nuevo)
```

**Impacto**: Todos los usuarios deberán iniciar sesión nuevamente.

#### 2. ENCRYPTION_KEY (Datos encriptados)

⚠️ **CRÍTICO**: Cambiar ENCRYPTION_KEY invalidará datos encriptados existentes.

```bash
# 1. Backup de datos encriptados
pg_dump $DATABASE_URL > backup_pre_rotation.sql

# 2. Desencriptar datos existentes (si es posible)
# 3. Generar nueva ENCRYPTION_KEY
# 4. Re-encriptar con nueva clave
# 5. Actualizar .env
```

**Nota**: Implementar migración de datos encriptados requiere script especializado.

#### 3. Contraseñas de Base de Datos

```bash
# 1. Cambiar contraseña en PostgreSQL
psql -U postgres -c "ALTER USER ats_user WITH PASSWORD 'nueva_password';"

# 2. Actualizar DATABASE_URL en .env
# 3. Reiniciar aplicación
```

#### 4. API Keys (OpenAI, WhatsApp, etc.)

- Rotar desde el dashboard del proveedor
- Actualizar en `backend/.env`
- Reiniciar aplicación

---

## Variables de Entorno

### Variables Requeridas

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SECRET_KEY` | Clave para firmar JWT | `aB3x...` (64 chars) |
| `DATABASE_URL` | URL de conexión a DB | `postgresql+asyncpg://...` |
| `DEFAULT_ADMIN_EMAIL` | Email del admin inicial | `admin@empresa.com` |
| `DEFAULT_ADMIN_PASSWORD` | Contraseña del admin | Mín. 12 chars en prod |

### Variables Opcionales

| Variable | Descripción | Default |
|----------|-------------|---------|
| `ENCRYPTION_KEY` | Clave Fernet (auto-generada) | - |
| `REDIS_URL` | URL de Redis | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | API Key de OpenAI | - |
| `WHATSAPP_*` | Configuración WhatsApp | - |

### Variables por Entorno

#### Desarrollo
```bash
DEBUG=true
ENVIRONMENT=development
WHATSAPP_MOCK_MODE=true
```

#### Producción
```bash
DEBUG=false
ENVIRONMENT=production
WHATSAPP_MOCK_MODE=false
# NUNCA usar '*' en CORS_ORIGINS
CORS_ORIGINS=https://tuapp.com,https://admin.tuapp.com
```

---

## Buenas Prácticas

### ✅ Hacer

1. **Usar variables de entorno** para TODOS los secretos
2. **Generar contraseñas automáticamente** cuando sea posible
3. **Rotar secretos** periódicamente (90 días máximo)
4. **Usar permisos restrictivos** en archivos de configuración
   ```bash
   chmod 600 backend/.env
   ```
5. **Hacer backups** antes de rotar secretos
6. **Usar gestores de secretos** en producción (AWS Secrets Manager, Vault, etc.)
7. **Auditar acceso** a secretos regularmente

### ❌ NUNCA Hacer

1. **NUNCA** commitear archivos `.env` a git
2. **NUNCA** hardcodear contraseñas en el código
3. **NUNCA** compartir secretos por email o chat
4. **NUNCA** usar contraseñas débiles (`password`, `123456`, `changeme`)
5. **NUNCA** exponer secrets en logs o errores
6. **NUNCA** usar la misma SECRET_KEY en múltiples entornos

### Comandos Útiles

```bash
# Verificar que .env no está en git
git ls-files | grep \\.env

# Si aparece, removerlo:
git rm --cached backend/.env
echo '.env' >> .gitignore
git commit -m "Remove .env from tracking"

# Validar fortaleza de configuración
python scripts/setup_secrets.py --check

# Generar nueva SECRET_KEY solamente
python scripts/generate_secrets.py
```

---

## Chequeo de Seguridad

### Validación Automática

```bash
# Valida configuración actual
python scripts/setup_secrets.py --check
```

Verifica:
- ✅ SECRET_KEY no es un placeholder
- ✅ DEFAULT_ADMIN_PASSWORD es segura (min 12 chars)
- ✅ DATABASE_URL no contiene passwords default
- ✅ No hay DEBUG=true en producción

### Auditoría Manual

```bash
# Buscar posibles secrets en código
grep -r "password.*=" --include="*.py" . | grep -v ".venv" | grep -v "__pycache__"
grep -r "SECRET_KEY" --include="*.py" . | grep -v ".venv"

# Revisar permisos de archivos
ls -la backend/.env
# Debería ser: -rw------- (solo owner puede leer/escribir)
```

---

## Respuesta a Incidentes

### Si un Secreto fue Expuesto

1. **Rotar inmediatamente**
   ```bash
   python scripts/setup_secrets.py --force
   ```

2. **Revocar tokens/sesiones**
   - Si SECRET_KEY: Todos los usuarios deben re-loguearse
   - Si API Key: Revocar en el dashboard del proveedor

3. **Auditar acceso**
   ```bash
   # Revisar logs de acceso
   grep "admin" logs/app.log
   ```

4. **Notificar**
   - Informar al equipo de seguridad
   - Documentar el incidente
   - Revisar políticas de prevención

### Contacto

- **Equipo de Seguridad**: security@tuempresa.com
- **On-Call**: +1-XXX-XXX-XXXX

---

## Referencias

- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Python Secrets](https://docs.python.org/3/library/secrets.html)
- [Fernet Encryption](https://cryptography.io/en/latest/fernet/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

## Historial de Cambios

| Fecha | Versión | Cambios |
|-------|---------|---------|
| 2025-02-17 | 1.0 | Documento inicial de seguridad |
