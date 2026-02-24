# 🔐 INFORME DE REVISIÓN - GESTIÓN DE SECRETOS Y CONFIGURACIÓN
## ATS Platform - Análisis de Seguridad

**Fecha:** 2026-02-17  
**Revisor:** Subagente de Seguridad  
**Proyecto:** ATS Preselection Platform

---

## 🚨 RESUMEN EJECUTIVO

**Nivel de Riesgo:** 🔴 **CRÍTICO**

Se han identificado **múltiples secretos expuestos** en el codebase, incluyendo contraseñas hardcodeadas, credenciales en archivos de configuración, y falta de mecanismos robustos de gestión de secretos. **Requiere atención inmediata antes de cualquier despliegue en producción.**

---

## 1️⃣ SECRETOS EXPUESTOS EN CÓDIGO

### 🔴 CRÍTICO - Secretos Hardcodeados

| Archivo | Línea | Secreto Expuesto | Nivel |
|---------|-------|------------------|-------|
| `backend/.env` | 13 | `SECRET_KEY=rrgLl3EXmuftXFWqCY446fJ4HFhLTfaH_CoG4OH7tGjSsmyek5` | 🔴 CRÍTICO |
| `backend/.env` | 21 | `DEFAULT_ADMIN_PASSWORD=ChangeMe123!` | 🔴 CRÍTICO |
| `backend/.env` | 7 | `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ats_platform` | 🔴 CRÍTICO |
| `backend/.env.example` | 7 | `DATABASE_URL=postgresql://postgres:password@localhost:5432/ats_platform` | 🟡 MEDIO |
| `backend/.env.example` | 11 | `SECRET_KEY=change-this-to-a-secure-random-string-min-32-chars` | 🟡 MEDIO |
| `backend/.env.example` | 21 | `DEFAULT_ADMIN_PASSWORD=ChangeMe123!` | 🟡 MEDIO |
| `backend/create_admin.py` | 32 | `password="Admin123!"` | 🔴 CRÍTICO |
| `backend/create_hh_tables.py` | 16 | `DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ats_platform"` | 🟠 ALTO |
| `backend/seed_headhunting_data.py` | 25 | `DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ats_platform"` | 🟠 ALTO |
| `docker-compose.yml` | 56 | `SECRET_KEY=${SECRET_KEY:-your-secret-key-change-in-production}` | 🟡 MEDIO |
| `docker-compose.yml` | 14-15 | `POSTGRES_USER: postgres` / `POSTGRES_PASSWORD: postgres` | 🟡 MEDIO |
| `docker-compose.yml` | 112-113 | `GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}` / `GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}` | 🟡 MEDIO |
| `scripts/demo_flow.sh` | 19 | `ADMIN_EMAIL="${ADMIN_EMAIL:-admin@topmanagement.com}"` | 🟡 MEDIO |
| `install-deps-manual.sh` | 55 | `CREATE USER ats_user WITH PASSWORD 'ats_password'` | 🟡 MEDIO |

### 🟠 ALTO - Credenciales en Scripts de Setup

```bash
# install-deps-manual.sh
sudo -u postgres psql -c "CREATE USER ats_user WITH PASSWORD 'ats_password';"
```

**Riesgo:** Credenciales de base de datos expuestas en scripts de instalación.

### 🟡 MEDIO - Tokens de Prueba

Los archivos de test contienen tokens mock que, aunque son solo para testing, podrían confundirse con credenciales reales:

| Archivo | Contenido |
|---------|-----------|
| `backend/tests/test_whatsapp_service.py:13` | `mock.WHATSAPP_ACCESS_TOKEN = "test_token"` |
| `backend/tests/test_whatsapp_service.py:17` | `mock.WHATSAPP_WEBHOOK_VERIFY_TOKEN = "test_verify_token"` |
| `backend/tests/test_whatsapp_service.py:18` | `mock.WHATSAPP_APP_SECRET = "test_app_secret"` |

---

## 2️⃣ SECRET MANAGEMENT

### Estado Actual: ❌ NO CUMPLE

| Aspecto | Estado | Descripción |
|---------|--------|-------------|
| **Secret Manager** | ❌ No implementado | Solo usa archivos `.env` |
| **Separación por entornos** | ⚠️ Parcial | Existe `.env.production` template pero sin gestión robusta |
| **Encriptación en reposo** | ✅ Parcial | Credenciales en BD usan Fernet |
| **Rotación de claves** | ❌ No implementada | Sin política definida |
| **Auditoría de acceso** | ⚠️ Básica | Solo logs de cambios, no de acceso a secretos |

### Implementación Actual

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    # ... resto de configuración desde .env
```

**Problemas identificados:**

1. **No se usa un Secret Manager externo** (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault)
2. **Los secretos están en archivos planos** (.env) que pueden ser comprometidos
3. **Sin encriptación de archivos .env** en el filesystem
4. **Permisos de archivos no verificados** automáticamente

---

## 3️⃣ ROTACIÓN DE CLAVES

### ❌ NO IMPLEMENTADA

| Tipo de Clave | Política Actual | Riesgo |
|---------------|-----------------|--------|
| **JWT SECRET_KEY** | Sin rotación | 🔴 Alto - Si se compromete, todas las sesiones son vulnerables |
| **DB Credentials** | Sin rotación | 🔴 Alto - Exposición prolongada |
| **API Keys (OpenAI, WhatsApp, Zoho)** | Sin rotación | 🔴 Alto - Acceso indefinido si se filtran |
| **Encryption Key (Fernet)** | Sin rotación | 🔴 Alto - Datos cifrados comprometidos |
| **Refresh Tokens** | 7 días | 🟡 Medio - Período relativamente largo |

### Código de Generación de Secrets

```python
# scripts/generate_secrets.py - EXISTE pero no está automatizado
def generate_secret_key(self, length: int = 64) -> str:
    alphabet = string.ascii_letters + string.digits + "_-"
    return ''.join(secrets.choice(alphabet) for _ in range(max(length, self.MIN_SECRET_LENGTH)))
```

**Problema:** El script existe pero no hay política de rotación programada ni automatizada.

---

## 4️⃣ AUDITORÍA

### Estado Actual: ⚠️ BÁSICO

#### Logs de Seguridad Existentes (`backend/app/core/security_logging.py`)

```python
class SecurityLogger:
    """Logger especializado para eventos de seguridad."""
    
    # Eventos logueados:
    - login_success / login_failure
    - logout
    - unauthorized_access
    - password_change_success / password_change_failure
    - user_modification
    - config_change
    - suspicious_activity
    - rate_limit_hit
    - token_refresh_success / token_refresh_failure
```

#### Auditoría de Configuraciones

```python
# backend/app/models/__init__.py
class Configuration(Base):
    """Configuración del sistema - almacena credenciales cifradas."""
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### Gaps Identificados

| Gap | Impacto | Prioridad |
|-----|---------|-----------|
| No hay logs de **quién accedió a qué secreto** | No trazable | 🔴 Alta |
| No hay alertas de **acceso sospechoso** a secretos | Detección tardía | 🔴 Alta |
| No hay registro de **uso de API keys** | Abuso no detectable | 🟠 Media |
| No hay rotación **forzada periódica** | Acumulación de riesgo | 🟠 Media |

---

## 5️⃣ PERMISOS MÍNIMOS

### Base de Datos

```python
# backend/.env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ats_platform
```

❌ **Problema:** Usa el usuario `postgres` (superadmin) en lugar de un usuario con permisos mínimos.

### Permisos de Archivos

```bash
# El script generate_secrets.py establece permisos correctos:
os.chmod(output_file, 0o600)  # Solo owner puede leer/escribir
```

⚠️ **Problema:** No hay verificación automática de permisos de archivos `.env` en producción.

### CORS

```python
# backend/app/core/config.py
def get_cors_origins(self) -> List[str]:
    origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    if self.ENVIRONMENT == 'production':
        origins = [o for o in origins if o != "*"]
    return origins
```

⚠️ **Problema:** El CORS en producción aún permite múltiples orígenes si están configurados.

---

## 6️⃣ ALMACENAMIENTO SEGURO EN BD

### ✅ Buenas Prácticas Implementadas

```python
# backend/app/models/__init__.py
class Configuration(Base):
    """Configuración del sistema - almacena credenciales cifradas."""
    value_encrypted = Column(Text, nullable=False)  # Valor cifrado
    is_encrypted = Column(Boolean, default=True)
```

```python
# backend/app/core/security.py
class EncryptionManager:
    """Gestiona el cifrado/descifrado de credenciales sensibles."""
    
    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        return self._fernet.encrypt(value.encode()).decode()
    
    def decrypt(self, encrypted_value: str) -> str:
        if not encrypted_value:
            return ""
        return self._fernet.decrypt(encrypted_value.encode()).decode()
```

### Flujo de Almacenamiento Seguro

```
1. Usuario ingresa credencial (ej: API key de WhatsApp)
2. ConfigurationService.set() → encrypt_value()
3. Se almacena value_encrypted en BD
4. Al leer: decrypt_value() → retorna valor plano
5. Cache en Redis (TTL 5 minutos)
```

---

## 7️⃣ PLAN DE MITIGACIÓN URGENTE

### FASE 1: Inmediata (Antes de cualquier despliegue)

| # | Acción | Responsable | Prioridad |
|---|--------|-------------|-----------|
| 1.1 | **Cambiar inmediatamente** el `SECRET_KEY` en producción | DevOps | 🔴 CRÍTICO |
| 1.2 | **Eliminar** el archivo `backend/.env` del repositorio Git | DevOps | 🔴 CRÍTICO |
| 1.3 | **Cambiar** contraseña del admin por defecto | Admin | 🔴 CRÍTICO |
| 1.4 | **Cambiar** credenciales de PostgreSQL | DBA | 🔴 CRÍTICO |
| 1.5 | **Revisar** Git history por secretos filtrados | DevOps | 🔴 CRÍTICO |

### FASE 2: Corto Plazo (1-2 semanas)

| # | Acción | Responsable | Prioridad |
|---|--------|-------------|-----------|
| 2.1 | Implementar **HashiCorp Vault** o **AWS Secrets Manager** | Arquitecto | 🔴 Alta |
| 2.2 | Crear usuario PostgreSQL con **permisos mínimos** | DBA | 🔴 Alta |
| 2.3 | Implementar **rotación automática** de JWT SECRET_KEY | Backend | 🔴 Alta |
| 2.4 | Agregar **auditoría completa** de acceso a secretos | Backend | 🟠 Media |
| 2.5 | Implementar **alertas** de uso anómalo de API keys | DevOps | 🟠 Media |
| 2.6 | Migrar credenciales de `.env` a **secret manager** | DevOps | 🔴 Alta |

### FASE 3: Mediano Plazo (1 mes)

| # | Acción | Responsable | Prioridad |
|---|--------|-------------|-----------|
| 3.1 | Implementar **política de rotación** de todas las claves | Seguridad | 🟠 Media |
| 3.2 | Agregar **scanning automático** de secretos en CI/CD | DevOps | 🟠 Media |
| 3.3 | Implementar **encryptación de archivos .env** | DevOps | 🟡 Baja |
| 3.4 | Crear **dashboard de auditoría** de secretos | Frontend | 🟡 Baja |

---

## 8️⃣ IMPLEMENTACIÓN RECOMENDADA: HASHICORP VAULT

### Ejemplo de Integración

```python
# backend/app/core/secrets.py (nuevo archivo)
import hvac
from app.core.config import settings

class VaultSecretsManager:
    """Gestor de secretos usando HashiCorp Vault."""
    
    def __init__(self):
        self.client = hvac.Client(
            url=settings.VAULT_ADDR,
            token=settings.VAULT_TOKEN
        )
    
    def get_secret(self, path: str, key: str) -> str:
        """Obtiene un secreto de Vault."""
        secret = self.client.secrets.kv.v2.read_secret_version(
            path=path
        )
        return secret['data']['data'][key]
    
    def rotate_secret(self, path: str, key: str, new_value: str):
        """Rota un secreto en Vault."""
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret={key: new_value}
        )

# Uso en config.py
class Settings(BaseSettings):
    # En lugar de:
    # SECRET_KEY: str = "hardcoded-secret"
    
    # Usar:
    @property
    def SECRET_KEY(self) -> str:
        vault = VaultSecretsManager()
        return vault.get_secret("ats-platform/jwt", "secret_key")
```

---

## 9️⃣ CHECKLIST DE VERIFICACIÓN

### Pre-Despliegue en Producción

- [ ] Todos los `.env` con secretos reales eliminados del repo
- [ ] Git history limpiado (usar `git-filter-repo` o BFG)
- [ ] Secret Manager implementado y configurado
- [ ] Credenciales de BD rotadas
- [ ] SECRET_KEY de JWT rotada
- [ ] Permisos de archivos verificados (600 para .env)
- [ ] Usuario DB con permisos mínimos creado
- [ ] Logs de auditoría de secretos habilitados
- [ ] Rotación automática configurada
- [ ] Alertas de seguridad configuradas

---

## 📊 RESUMEN DE RIESGOS

| Categoría | Riesgo | Impacto | Probabilidad | Estado |
|-----------|--------|---------|--------------|--------|
| Secretos hardcodeados | 🔴 Crítico | Total | Alta | **Activo** |
| Sin Secret Manager | 🔴 Crítico | Alto | Media | **Activo** |
| Sin rotación de claves | 🔴 Alto | Alto | Media | **Activo** |
| Permisos DB excesivos | 🟠 Alto | Alto | Baja | **Activo** |
| Auditoría insuficiente | 🟠 Medio | Medio | Media | **Activo** |
| CORS permisivo | 🟡 Medio | Medio | Baja | **Activo** |

---

## 📚 REFERENCIAS

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [HashiCorp Vault Best Practices](https://developer.hashicorp.com/vault/docs/concepts)
- [AWS Secrets Manager Rotation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotate-secrets.html)
- [GitGuardian - Securing Secrets in Git](https://www.gitguardian.com/)

---

**Fin del Informe**

*Generado: 2026-02-17*  
*Clasificación: CONFIDENCIAL*
