# Configuración de Integraciones

Esta guía documenta cómo configurar las integraciones con sistemas externos.

## Tabla de Contenidos

1. [Zoho Recruit](#zoho-recruit)
2. [Odoo](#odoo)
3. [LinkedIn](#linkedin)
4. [Webhooks](#webhooks)
5. [Sincronización Programada](#sincronización-programada)

---

## Zoho Recruit

### 1. Crear Aplicación en Zoho

1. Ve a [Zoho Developer Console](https://api-console.zoho.com/)
2. Clic en "Add Client" → "Server-based Applications"
3. Completa:
   - **Client Name**: ATS Platform
   - **Homepage URL**: `https://tu-dominio.com`
   - **Authorized Redirect URIs**: `https://tu-dominio.com/api/v1/config/zoho/callback`
4. Guarda el **Client ID** y **Client Secret**

### 2. Configurar en ATS Platform

```bash
curl -X POST http://localhost:8000/api/v1/config/zoho \
  -H "Authorization: Bearer TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "TU_CLIENT_ID",
    "client_secret": "TU_CLIENT_SECRET",
    "refresh_token": "",
    "redirect_uri": "http://localhost:8000/api/v1/config/zoho/callback"
  }'
```

### 3. Obtener Refresh Token (OAuth2 Flow)

```bash
# 1. Obtener URL de autorización
curl http://localhost:8000/api/v1/config/zoho/auth-url \
  -H "Authorization: Bearer TU_TOKEN"

# 2. Abrir URL en navegador y autorizar
# 3. Zoho redirigirá al callback con ?code=XXX

# 4. El código se procesa automáticamente y guarda el refresh_token
```

### 4. Probar Conexión

```bash
curl -X POST http://localhost:8000/api/v1/config/zoho/test \
  -H "Authorization: Bearer TU_TOKEN"
```

### 5. Sincronización Manual

```bash
# Sync completa
curl -X POST http://localhost:8000/api/v1/config/zoho/sync \
  -H "Authorization: Bearer TU_TOKEN" \
  -d '{"full_sync": true, "sync_jobs": true, "sync_candidates": true}'

# Sync incremental (solo cambios recientes)
curl -X POST http://localhost:8000/api/v1/config/zoho/sync \
  -H "Authorization: Bearer TU_TOKEN" \
  -d '{"full_sync": false}'
```

### Mapeo de Campos Zoho → ATS

| Campo Zoho | Campo ATS | Notas |
|------------|-----------|-------|
| Job_Opening_ID | zoho_job_id | Identificador único |
| Job_Opening_Name | title | Título del puesto |
| Job_Description | description | HTML soportado |
| Department | department | Nombre del departamento |
| Location | location | Ubicación del puesto |
| Status | status | Mapeo: Active→active, Draft→draft, etc. |
| Candidate_ID | zoho_candidate_id | Identificador único |
| First_Name + Last_Name | full_name | Concatenado automáticamente |
| Email | email | Normalizado a minúsculas |
| Phone | phone | Normalizado (solo dígitos) |
| Stage | status | Mapeo de etapas de reclutamiento |

### Rate Limits

- **100 requests/minuto** por usuario
- **200 registros/batch** máximo
- Reintentos automáticos con exponential backoff

---

## Odoo

### 1. Configurar Usuario API en Odoo

1. Ve a **Settings** → **Users & Companies** → **Users**
2. Crea o selecciona un usuario para integración
3. Activa **API Key** y genera una nueva clave
4. Asigna permisos:
   - `hr_recruitment.group_hr_recruitment_user`
   - `base.group_user`

### 2. Verificar Modelos

Asegúrate de que los modelos estén disponibles:
- `hr.job` - Puestos de trabajo
- `hr.applicant` - Candidatos
- `hr.recruitment.stage` - Etapas del proceso

### 3. Configurar en ATS Platform

```bash
curl -X POST http://localhost:8000/api/v1/config/odoo \
  -H "Authorization: Bearer TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://tu-odoo.odoo.com",
    "database": "tu_base_datos",
    "username": "api_user@tuempresa.com",
    "api_key": "TU_API_KEY",
    "job_model": "hr.job",
    "applicant_model": "hr.applicant"
  }'
```

### 4. Probar Conexión

```bash
curl -X POST http://localhost:8000/api/v1/config/odoo/test \
  -H "Authorization: Bearer TU_TOKEN"
```

### 5. Sincronización

```bash
# Sync completa
curl -X POST http://localhost:8000/api/v1/config/odoo/sync \
  -H "Authorization: Bearer TU_TOKEN" \
  -d '{"full_sync": true}'

# Bidireccional: enviar candidato a Odoo
# (Se hace automáticamente al crear candidatos con source=odoo)
```

### Mapeo de Campos Odoo → ATS

| Campo Odoo | Campo ATS | Notas |
|------------|-----------|-------|
| id | external_id | ID numérico de Odoo |
| name | title | Nombre del puesto |
| description | description | HTML convertido a texto |
| department_id[1] | department | Nombre del departamento |
| state | status | recruit→active, done→closed |
| name (applicant) | full_name | Nombre completo |
| email_from | email | Email del candidato |
| partner_mobile | phone | Teléfono móvil |
| stage_id[1] | status | Mapeo de etapas |

### Campos Personalizados Recomendados

Para mejor sincronización, crear en Odoo:

1. **En hr.job**:
   - `x_zoho_job_id` (char) - Para sincronización con Zoho
   
2. **En hr.applicant**:
   - `x_linkedin_url` (char) - URL de LinkedIn
   - `x_zoho_candidate_id` (char) - ID de Zoho

---

## LinkedIn

### 1. Crear Aplicación en LinkedIn

1. Ve a [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Crea una nueva app
3. Solicita los productos:
   - **Sign In with LinkedIn** (obligatorio)
   - **Share on LinkedIn** (opcional)
4. En **Auth** tab, configura:
   - **Authorized Redirect URLs**: `https://tu-dominio.com/api/v1/config/linkedin/callback`
5. Guarda **Client ID** y **Client Secret**

### 2. Configurar en ATS Platform

```bash
curl -X POST http://localhost:8000/api/v1/config/linkedin \
  -H "Authorization: Bearer TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "TU_CLIENT_ID",
    "client_secret": "TU_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8000/api/v1/config/linkedin/callback"
  }'
```

### 3. OAuth2 Flow

```bash
# 1. Obtener URL de autorización
curl http://localhost:8000/api/v1/config/linkedin/auth-url \
  -H "Authorization: Bearer TU_TOKEN"

# 2. Redirigir usuario a esa URL
# 3. Usuario autoriza la app
# 4. LinkedIn redirige al callback con ?code=XXX
# 5. Tokens guardados automáticamente
```

### 4. Importar Candidato desde LinkedIn

```bash
# Primero el usuario debe autorizar (OAuth2)
# Luego importar por URL:

POST /api/v1/candidates/import-linkedin
{
  "linkedin_url": "https://www.linkedin.com/in/john-doe",
  "job_opening_id": "uuid-del-job"
}
```

### Scopes de LinkedIn

| Scope | Descripción | Requerido |
|-------|-------------|-----------|
| `r_liteprofile` | Nombre, foto, headline | Sí |
| `r_emailaddress` | Email principal | Sí |
| `r_basicprofile` | Experiencia, educación | Sí |

### Limitaciones

- **500 requests/día** para Basic Profile
- No se permite "scraping" masivo
- El candidato debe autorizar explícitamente
- Para búsqueda de candidatos se requiere [LinkedIn Partnership Program](https://developer.linkedin.com/partner-programs)

---

## Webhooks

### Configuración de Webhooks

#### Zoho Recruit

1. En Zoho, ve a **Setup** → **Developer Space** → **Webhooks**
2. Crea nuevo webhook:
   - **URL**: `https://tu-dominio.com/api/v1/config/webhooks/zoho`
   - **Method**: POST
   - **Module**: JobOpenings, Candidates
   - **Events**: Create, Edit, Delete
3. Opcional: Configurar token de seguridad

#### Odoo

1. Instala módulo `webhook` o usa **Automated Actions**:
2. **Settings** → **Technical** → **Automation** → **Automated Actions**
3. Crear acción:
   - **Model**: hr.job / hr.applicant
   - **Trigger**: On Create, On Update
   - **Action**: Execute Python Code
   ```python
   import requests
   requests.post(
       "https://tu-dominio.com/api/v1/config/webhooks/odoo",
       json={
           "model": model._name,
           "action": "create" if not record.exists() else "write",
           "data": record.read()[0]
       },
       headers={"X-Webhook-Secret": "TU_SECRETO"}
   )
   ```

### Verificación de Webhooks

Los webhooks incluyen:
- **HTTPS obligatorio**
- **Token de verificación** (en URL o headers)
- **Validación de firma** (Odoo)

---

## Sincronización Programada

### Configurar Celery Beat

En `celeryconfig.py` o `app/tasks/__init__.py`:

```python
celery_app.conf.beat_schedule = {
    "sync-zoho-hourly": {
        "task": "app.services.sync_service.scheduled_sync",
        "schedule": 3600.0,  # Cada hora
        "args": ("zoho", False, True, True)
    },
    "sync-odoo-hourly": {
        "task": "app.services.sync_service.scheduled_sync",
        "schedule": 3600.0,
        "args": ("odoo", False, True, True)
    },
    "check-sync-health": {
        "task": "app.services.sync_service.check_sync_health",
        "schedule": 300.0  # Cada 5 minutos
    }
}
```

### Iniciar Workers

```bash
# Worker general
celery -A app.tasks worker --loglevel=info -Q sync,default

# Scheduler
celery -A app.tasks beat --loglevel=info
```

### Monitoreo

Ver estado de sincronizaciones:

```bash
# Estado de conectores
curl http://localhost:8000/api/v1/config/connectors/status \
  -H "Authorization: Bearer TU_TOKEN"

# Salud de syncs
curl http://localhost:8000/api/v1/config/sync/health \
  -H "Authorization: Bearer TU_TOKEN"

# Logs recientes
curl "http://localhost:8000/api/v1/config/sync/logs?source=zoho&limit=20" \
  -H "Authorization: Bearer TU_TOKEN"
```

---

## Troubleshooting

### Error: "Circuit breaker is OPEN"

El servicio externo está fallando repetidamente. Verificar:
1. Conectividad de red
2. Credenciales válidas
3. Rate limits no excedidos

El circuito se cierra automáticamente después de 60s (configurable).

### Error: "Rate limit exceeded"

Se han excedido los límites de la API:
- Zoho: 100 req/minuto
- LinkedIn: 500 req/día
- Odoo: No tiene límite estricto (10 req/seg recomendado)

Los reintentos automáticos usan exponential backoff.

### Webhooks no llegan

Verificar:
1. URL accesible desde internet
2. HTTPS válido (certificado no expirado)
3. Firewall permite requests
4. Logs en `/var/log/ats-platform/webhooks.log`

### Tokens expirados

Los tokens se refrescan automáticamente. Si falla:
1. Reconfigurar con nuevo refresh_token (Zoho)
2. Re-hacer OAuth2 flow (LinkedIn)
3. Verificar que api_key no expiró (Odoo)

---

## Seguridad

### Credenciales

- Todas las credenciales se **encriptan** con Fernet antes de guardar
- Las claves de API nunca se loguean
- Las respuestas de API enmascaran datos sensibles

### Webhooks

- Validación de firmas HMAC (donde aplique)
- Tokens de verificación en URL
- HTTPS obligatorio para webhooks

### OAuth2

- Tokens almacenados en cache con TTL
- Refresh automático antes de expirar
- Scope mínimo necesario

---

## Referencia de API

### Endpoints de Configuración

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/config/status` | Estado de todas las integraciones |
| GET | `/config/connectors/status` | Estado detallado de conectores |
| GET/POST | `/config/zoho` | Configuración Zoho |
| POST | `/config/zoho/test` | Probar conexión Zoho |
| GET | `/config/zoho/auth-url` | URL OAuth2 Zoho |
| POST | `/config/zoho/callback` | Callback OAuth2 |
| POST | `/config/zoho/sync` | Sincronización manual |
| GET/POST | `/config/odoo` | Configuración Odoo |
| POST | `/config/odoo/test` | Probar conexión Odoo |
| POST | `/config/odoo/sync` | Sincronización manual |
| GET/POST | `/config/linkedin` | Configuración LinkedIn |
| POST | `/config/linkedin/test` | Probar conexión LinkedIn |
| GET | `/config/linkedin/auth-url` | URL OAuth2 LinkedIn |
| POST | `/config/webhooks/zoho` | Webhook Zoho |
| POST | `/config/webhooks/odoo` | Webhook Odoo |
| GET | `/config/sync/logs` | Logs de sincronización |
| GET | `/config/sync/health` | Salud de sincronizaciones |
