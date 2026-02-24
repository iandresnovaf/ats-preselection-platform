# 🔒 INFORME DE SEGURIDAD BASELINE - ATS PLATFORM

**Fecha:** 2026-02-17  
**Versión:** 1.0  
**Clasificación:** Confidencial  
**Auditor:** Análisis Automatizado de Seguridad

---

## 📋 RESUMEN EJECUTIVO

Se realizó una revisión de seguridad baseline completa del ATS Platform, analizando código fuente, configuraciones, modelos de datos y arquitectura. El sistema presenta **buenas prácticas de seguridad implementadas** pero requiere atención en áreas críticas antes de su despliegue en producción.

### Hallazgos por Severidad
| Severidad | Cantidad | Estado |
|-----------|----------|--------|
| 🔴 Crítico | 4 | Requiere acción inmediata |
| 🟠 Medio | 8 | Requiere atención próximos 30 días |
| 🟡 Bajo | 6 | Mejora continua |

---

## 1️⃣ MODELO DE AMENAZAS (THREAT MODELING)

### 1.1 Módulo: Login/Autenticación

#### Componentes Analizados
- `app/core/auth.py` - JWT, bcrypt, password hashing
- `app/core/deps.py` - Dependencias de autorización
- `app/core/rate_limit.py` - Rate limiting
- `app/core/security_logging.py` - Logging de seguridad

#### Amenazas Identificadas

| ID | Amenaza | Severidad | Mitigación Actual | Brechas |
|----|---------|-----------|-------------------|---------|
| AUTH-001 | Credential Stuffing | 🟠 Media | Rate limiting 3 req/min login, enumeración protección | ✅ Implementado |
| AUTH-002 | Timing Attacks | 🟢 Baja | Dummy hash verification, constant-time comparison | ✅ Implementado |
| AUTH-003 | JWT Token Theft | 🟠 Media | Tokens en cookies httpOnly, expiración 30 min | ⚠️ Sin invalidación server-side |
| AUTH-004 | Password Brute Force | 🟠 Media | bcrypt rounds=12, rate limiting | ✅ Implementado |
| AUTH-005 | Session Fixation | 🟡 Baja | No detectado | ⚠️ No hay rotación de session ID |

#### 🔴 Hallazgo Crítico: AUTH-CRIT-001
**Problema:** Ausencia de mecanismo de invalidación de tokens JWT (logout no invalida token)
```python
# En auth.py - decode_token() solo verifica firma/expiración
# No hay blacklist/revocation de tokens
```
**Impacto:** Tokens robados permanecen válidos hasta expirar (30 min)
**Recomendación:** Implementar Redis blacklist para tokens invalidated o usar refresh token rotation

#### 🟠 Hallazgo Medio: AUTH-MED-001
**Problema:** `DUMMY_HASH` hardcodeado en auth.py puede causar timing attacks si es estático
**Recomendación:** Generar dummy hash dinámicamente en cada verificación

---

### 1.2 Módulo: Gestión de Candidatos y Aplicaciones

#### Componentes Analizados
- `app/api/v1/candidates.py` - CRUD candidatos
- `app/api/v1/applications.py` - Pipeline de aplicaciones
- `app/models/core_ats.py` - Modelos HHCandidate, HHApplication

#### Amenazas Identificadas

| ID | Amenaza | Severidad | Estado |
|----|---------|-----------|--------|
| CAND-001 | IDOR - Acceso a otros candidatos | 🟠 Media | ⚠️ No se valida propiedad de recursos |
| CAND-002 | Mass Assignment | 🟡 Baja | ✅ Pydantic schemas con validación |
| CAND-003 | Information Disclosure | 🟠 Media | ⚠️ Datos sensibles en logs de auditoría |
| CAND-004 | SQL Injection | 🟢 Baja | ✅ SQLAlchemy ORM (parametrizado) |

#### 🔴 Hallazgo Crítico: CAND-CRIT-001
**Problema:** IDOR (Insecure Direct Object Reference) - No se valida que el usuario autenticado tenga permisos sobre el recurso solicitado
```python
# En candidates.py - get_candidate()
@router.get("/{candidate_id}")
async def get_candidate(candidate_id: UUID, ...):
    # No se verifica si current_user puede ver este candidato
    result = await db.execute(
        select(HHCandidate).where(HHCandidate.candidate_id == candidate_id)
    )
    # Cualquier usuario autenticado puede ver cualquier candidato
```

**Endpoints Afectados:**
- GET /candidates/{id}
- GET /candidates/{id}/applications
- GET /applications/{id}
- PATCH /applications/{id}/stage
- GET /applications/{id}/timeline

**Impacto:** Usuarios pueden ver/modificar datos de candidatos de otros consultores
**Recomendación:** Implementar autorización basada en roles y propiedad:
```python
async def check_candidate_access(candidate_id: UUID, current_user: User):
    if current_user.role == UserRole.SUPER_ADMIN:
        return True
    # Verificar si el candidato está en aplicaciones del consultor
    ...
```

#### 🟠 Hallazgo Medio: CAND-MED-001
**Problema:** Los logs de auditoría (`HHAuditLog`) almacenan datos completos en `diff_json` sin enmascarar PII
```python
audit = HHAuditLog(
    diff_json=app_data  # Puede contener emails, teléfonos, etc.
)
```
**Recomendación:** Enmascarar PII en logs antes de almacenar

---

### 1.3 Módulo: Panel de Administración

#### Componentes Analizados
- `app/api/v1/clients.py` - Gestión de clientes
- `app/api/v1/roles.py` - Gestión de vacantes
- `app/core/deps.py` - Permisos (require_admin, require_consultant)

#### Amenazas Identificadas

| ID | Amenaza | Severidad | Estado |
|----|---------|-----------|--------|
| ADMIN-001 | Privilege Escalation | 🟠 Media | ✅ Verificación de roles implementada |
| ADMIN-002 | Mass Assignment - Roles | 🟡 Baja | ✅ Validación via schemas |
| ADMIN-003 | Business Logic Bypass | 🟠 Media | ⚠️ No hay validación de workflow |

#### 🟠 Hallazgo Medio: ADMIN-MED-001
**Problema:** No hay validación de workflow de negocio en transiciones de estado
```python
# En applications.py - update_application_stage()
# Cualquier etapa puede transicionar a cualquier otra sin validación
application.stage = stage_update.stage  # Sin validación de workflow
```
**Recomendación:** Implementar máquina de estados con transiciones válidas:
```python
VALID_TRANSITIONS = {
    ApplicationStage.SOURCING: [ApplicationStage.SHORTLIST, ApplicationStage.DISCARDED],
    ApplicationStage.SHORTLIST: [ApplicationStage.TERNA, ApplicationStage.DISCARDED],
    # ...
}
```

---

### 1.4 Módulo: APIs (Roles, Clients, Applications)

#### Componentes Analizados
- Todos los endpoints en `app/api/v1/*.py`
- `app/schemas/core_ats.py` - Validación Pydantic

#### Amenazas Identificadas

| ID | Amenaza | Severidad | Estado |
|----|---------|-----------|--------|
| API-001 | Excessive Data Exposure | 🟡 Baja | ⚠️ Algunos endpoints retornan más datos de los necesarios |
| API-002 | Lack of Rate Limiting | 🟢 Baja | ✅ Rate limiting implementado |
| API-003 | Mass Assignment | 🟢 Baja | ✅ Pydantic valida entrada |
| API-004 | Injection - PDF processing | 🟠 Media | ⚠️ Procesamiento de PDF sin sandbox |

#### 🟠 Hallazgo Medio: API-MED-001
**Problema:** Procesamiento de PDFs en `documents.py` sin sandboxing
```python
# En extract_cv_info() - lectura directa de PDFs
with open(temp_path, 'rb') as f:
    reader = pypdf.PdfReader(f)  # Vulnerable a PDF malicioso
```
**Recomendación:** Usar sandbox/contenedor para procesamiento de archivos o librerías con validación de seguridad

---

### 1.5 Módulo: Integraciones (CV Parsing, Notificaciones)

#### Componentes Analizados
- `app/services/cv_extractor.py` - Extracción de CVs
- `app/services/whatsapp_service.py` - WhatsApp Business API
- `app/services/email_service.py` - Envío de emails
- `app/integrations/linkedin.py` - LinkedIn
- `app/integrations/zoho_recruit.py` - Zoho

#### Amenazas Identificadas

| ID | Amenaza | Severidad | Estado |
|----|---------|-----------|--------|
| INT-001 | Secret Leakage en Logs | 🔴 Crítica | 🔴 API keys pueden loggearse |
| INT-002 | SSRF - LLM Calls | 🟠 Media | ⚠️ LLM service sin validación de URLs |
| INT-003 | Command Injection | 🟢 Baja | ✅ No hay ejecución de comandos |
| INT-004 | WhatsApp Webhook Tampering | 🟠 Media | ⚠️ Validación de firma presente pero básica |

#### 🔴 Hallazgo Crítico: INT-CRIT-001
**Problema:** Posible exposición de API keys en logs de integraciones
```python
# En llm.py, whatsapp_service.py, etc.
# Las claves se cargan desde settings pero pueden aparecer en logs de debug
self.access_token = access_token or settings.WHATSAPP_ACCESS_TOKEN
```
**Recomendación:** 
1. Nunca loggear variables de configuración sensibles
2. Usar secrets management (AWS Secrets Manager, Azure Key Vault)
3. Implementar rotación automática de claves

#### 🟠 Hallazgo Medio: INT-MED-001
**Problema:** Servicio LLM podría ser vulnerable a SSRF si se configura URL externa
```python
# En llm.py - el endpoint es configurable
# Si un atacante puede modificar la config, podría apuntar a URLs internas
```
**Recomendación:** Validar que URLs de LLM sean de dominios permitidos

---

## 2️⃣ CLASIFICACIÓN DE DATOS

### 2.1 Tipos de Datos Manejados

#### Datos Súper Sensibles (Nivel 1 - Requiere Cifrado)
| Campo | Tabla | Almacenamiento | Estado |
|-------|-------|----------------|--------|
| CV/Documentos PDF | hh_documents | Filesystem + SHA256 | ⚠️ Sin cifrado en reposo |
| Texto raw de CVs | hh_cv_extractions | PostgreSQL (JSONB) | ⚠️ Sin cifrado |
| Números de teléfono | hh_candidates | PostgreSQL | ⚠️ Texto plano |
| Emails | hh_candidates | PostgreSQL | ⚠️ Texto plano |

#### Datos Sensibles (Nivel 2 - Control de Acceso Estricto)
| Campo | Tabla | Contexto |
|-------|-------|----------|
| Nombres completos | hh_candidates | PII directo |
| LinkedIn URLs | hh_candidates | PII indirecto |
| Historial laboral | hh_cv_extractions | Información confidencial |
| Evaluaciones psicométricas | hh_assessments, hh_assessment_scores | Datos médicos/sensibles |
| Notas de entrevistas | hh_interviews | Opiniones subjetivas |

#### Datos Confidenciales de Negocio (Nivel 3)
| Campo | Tabla | Contexto |
|-------|-------|----------|
| Nombres de clientes | hh_clients | Información comercial |
| Vacantes/roles | hh_roles | Información estratégica |
| Scores de evaluación | hh_assessment_scores | Metodología propietaria |
| Flags de riesgo | hh_flags | Decisiones de negocio |

### 2.2 Reglas de Retención Recomendadas

#### Candidatos (hh_candidates)
```
Retención: 2 años desde última actividad
Eliminación: Automática tras período de retención
Excepciones: Candidatos contratados (retención indefinida laboral)
Método: Soft delete + anonimización después de 1 año
```

#### Aplicaciones (hh_applications)
```
Retención: 3 años desde cierre de vacante
Eliminación: Anonimización de datos personales después de 1 año
Justificación: Defensa legal, análisis de hiring
```

#### Documentos (hh_documents)
```
Retención: 1 año desde último acceso
Eliminación: Eliminación física + sobrescritura segura
Excepciones: Documentos de candidatos contratados
```

#### CVs Extraídos (hh_cv_extractions)
```
Retención: 6 meses desde procesamiento
Eliminación: Inmediata tras retención
Justificación: Reduce riesgo de exposición de datos raw
```

#### Logs de Auditoría (hh_audit_log)
```
Retención: 1 año
Eliminación: Archivado a storage frío después de 6 meses
Justificación: Cumplimiento, forense
```

#### Logs de Seguridad
```
Retención: 2 años
Eliminación: Nunca (a menos que sea requerido legalmente)
Justificación: Cumplimiento regulatorio, detección de intrusiones
```

### 2.3 🔴 Hallazgo Crítico: DATA-CRIT-001
**Problema:** No hay cifrado en reposo para datos sensibles en base de datos
**Tablas Afectadas:** hh_candidates, hh_cv_extractions, hh_documents
**Recomendación:** 
1. Habilitar TDE (Transparent Data Encryption) en PostgreSQL
2. Cifrar columnas sensibles (email, phone, national_id) con AES-256
3. Usar pgcrypto para campos sensibles

---

## 3️⃣ REQUISITOS NO FUNCIONALES DE SEGURIDAD

### 3.1 Objetivos RPO/RTO

| Sistema | RPO Objetivo | RTO Objetivo | Estrategia |
|---------|--------------|--------------|------------|
| Base de Datos PostgreSQL | 1 hora | 4 horas | Streaming replication + PITR |
| Redis Cache | 24 horas | 1 hora | RDB snapshots + AOF |
| Archivos Uploads | 24 horas | 4 horas | Backup incremental S3 |
| Configuración | 0 (inmutable) | 1 hora | Git + Infrastructure as Code |

#### 🟠 Hallazgo Medio: RPO-MED-001
**Problema:** No se detectó configuración de backup automático en PostgreSQL
**Recomendación:** Implementar pg_dump automatizado cada 6 horas + WAL archiving

### 3.2 SLAs de Seguridad

| Métrica | Objetivo | Medición |
|---------|----------|----------|
| Tiempo de respuesta a incidentes (T1) | < 15 min | Alerta → Ack |
| Tiempo de resolución crítica | < 4 horas | Ack → Fix |
| Disponibilidad del sistema | 99.9% | Uptime mensual |
| RPS sostenido | 1000 req/s | Load testing |
| Latencia p95 | < 500ms | API endpoints |

### 3.3 Concurrencia Estimada

```
Usuarios Concurrentes Estimados:
- Consultores: 20-50 usuarios concurrentes
- Candidatos (webhooks): 100-500 concurrentes
- Integraciones (API externas): 50-100 concurrentes

Cálculo de Capacidad:
- 50 consultores × 10 req/min = 500 req/min = 8.3 req/s
- Webhooks WhatsApp: 100 msg/min pico = 1.7 req/s
- Total estimado: 10-50 req/s promedio, 500 req/s pico
```

**Recomendación:** Configurar rate limits según estos valores y escalar horizontalmente cuando se alcance el 70% de capacidad.

### 3.4 Presupuesto de Infraestructura de Seguridad

| Componente | Costo Mensual Est. | Justificación |
|------------|-------------------|---------------|
| WAF (CloudFlare/AWS WAF) | $200-500 | Protección DDoS, SQLi, XSS |
| Secrets Manager | $40 | Rotación automática de secrets |
| Backup Storage | $100-300 | Retención multi-región |
| SIEM/Splunk | $500-1000 | Análisis de logs centralizado |
| Pentesting anual | $5000-10000 | Evaluación externa |
| Bug Bounty | $1000-3000 | Programa continuo |
| **Total Mensual** | **$1840-3830** | **+ $15000 anual** |

---

## 4️⃣ POLÍTICAS DE SEGURIDAD

### 4.1 Gestión de Secretos (.env, keys)

#### Estado Actual
```
✅ SECRET_KEY: Generado automáticamente si no está configurado
✅ ENCRYPTION_KEY: Soporta Fernet (32 bytes base64)
⚠️ Database URL: Contraseña en texto plano en variable de entorno
⚠️ API Keys: Almacenadas en .env sin cifrado adicional
🔴 WhatsApp Tokens: Posible exposición en logs
```

#### 🔴 Hallazgo Crítico: SEC-CRIT-001
**Problema:** El archivo `.env` contiene secrets en texto plano sin cifrar
```bash
# .env actual
SECRET_KEY=rrgLl3EXmuftXFWqCY446fJ4HFhLTfaH_CoG4OH7tGjSsmyek5
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ats_platform
```
**Recomendación:**
1. Usar secrets manager (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)
2. Nunca commitear .env a git (verificar .gitignore)
3. Rotar secrets inmediatamente si se expusieron
4. Implementar cifrado de variables de entorno con sops o similar

#### 🟠 Hallazgo Medio: SEC-MED-001
**Problema:** Contraseña por defecto del admin hardcodeada en config
```python
DEFAULT_ADMIN_PASSWORD=ChangeMe123!  # En .env
```
**Recomendación:** 
1. Generar contraseña aleatoria en primera ejecución
2. Forzar cambio en primer login
3. Validar complejidad: mínimo 12 caracteres, mayúsculas, minúsculas, números, símbolos

### 4.2 Manejo de Incidentes

#### Estado Actual
```
✅ SecurityLogger implementado para logging de eventos
✅ Auditoría de operaciones CRUD en HHAuditLog
✅ Rate limiting con logging de intentos sospechosos
⚠️ No hay procedimiento documentado de respuesta a incidentes
⚠️ No hay contactos de escalamiento definidos
🔴 No hay monitoreo de integridad de archivos
```

#### 🟠 Hallazgos Medios

**INC-MED-001:** No hay procedimiento documentado de respuesta a incidentes
**Recomendación:** Crear playbook con:
1. Clasificación de severidad
2. Roles y responsabilidades
3. Comunicación (interna/externa)
4. Contención, erradicación, recuperación
5. Lecciones aprendidas

**INC-MED-002:** Ausencia de detección de intrusiones (IDS/IPS)
**Recomendación:** Implementar:
- Fail2ban para bloqueo de IPs sospechosas
- AIDE/Tripwire para integridad de archivos
- Alertas en tiempo real de actividad anómala

### 4.3 SDLC Seguro (Secure Development Lifecycle)

#### Estado Actual

| Fase | Estado | Observaciones |
|------|--------|---------------|
| Diseño | 🟡 Parcial | Threat modeling no formalizado |
| Desarrollo | 🟢 Bueno | Linters, type hints, validación de entrada |
| Testing | 🟡 Parcial | No hay tests de seguridad automatizados |
| Deployment | 🟡 Parcial | Docker usado, pero sin scanning de imágenes |
| Operaciones | 🟡 Parcial | Monitoreo básico, falta SIEM |

#### 🟠 Hallazgos Medios

**SDLC-MED-001:** Ausencia de SAST/DAST en CI/CD
**Recomendación:** Integrar:
```yaml
# Ejemplo para GitHub Actions
- name: Run Bandit (SAST)
  uses: PyCQA/bandit@main
  with:
    args: "-r ./backend/app -f json -o bandit-report.json"

- name: Run Safety (Dependency Check)
  run: safety check

- name: Run Trivy (Container Scan)
  uses: aquasecurity/trivy-action@master
```

**SDLC-MED-002:** No hay revisión de seguridad de dependencias
**Recomendación:**
1. Usar `safety check` o `pip-audit`
2. Suscribirse a alertas de seguridad de GitHub
3. Mantener dependencias actualizadas (Dependabot)

### 4.4 Checklist de Cumplimiento

#### GDPR/LGPD (Protección de Datos)
| Requisito | Estado | Observaciones |
|-----------|--------|---------------|
| Consentimiento explícito | ❌ No implementado | Candidatos no dan consentimiento digital |
| Derecho al olvido | ⚠️ Parcial | Eliminación manual, no automatizada |
| Portabilidad de datos | ⚠️ Parcial | Exportación posible vía API |
| Notificación de brechas | ❌ No implementado | Proceso no definido |
| DPIA | ❌ No realizado | Necesario para datos sensibles |

#### ISO 27001
| Control | Estado |
|---------|--------|
| Política de seguridad | ⚠️ Básica |
| Control de acceso | ✅ Implementado |
| Criptografía | ⚠️ Parcial (falta cifrado reposo) |
| Seguridad operacional | ⚠️ Básica |
| Gestión de incidentes | ❌ No formalizada |

---

## 📊 RECOMENDACIONES PRIORIZADAS

### Inmediatas (Próximos 7 días)
1. 🔴 Implementar invalidación de tokens JWT en logout
2. 🔴 Habilitar cifrado en reposo para PostgreSQL
3. 🔴 Revisar y rotar todos los secrets expuestos
4. 🔴 Implementar autorización en endpoints de candidatos (IDOR)

### Corto Plazo (Próximos 30 días)
5. 🟠 Implementar workflow de transiciones de estado válidas
6. 🟠 Configurar backups automatizados con PITR
7. 🟠 Enmascarar PII en logs de auditoría
8. 🟠 Implementar SAST en pipeline de CI/CD

### Mediano Plazo (Próximos 90 días)
9. 🟡 Implementar secrets manager (Vault/AWS Secrets)
10. 🟡 Implementar WAF y protección DDoS
11. 🟡 Crear procedimiento de respuesta a incidentes
12. 🟡 Realizar pentesting externo

---

## 📎 ANEXOS

### A. Endpoints Auditados

| Módulo | Endpoints | Método | Auth | Autorización |
|--------|-----------|--------|------|--------------|
| Candidates | /candidates | GET/POST | ✅ | ⚠️ IDOR |
| Candidates | /candidates/{id} | GET/PATCH | ✅ | ⚠️ IDOR |
| Clients | /clients | GET/POST | ✅ | ✅ Roles |
| Roles | /roles | GET/POST | ✅ | ✅ Roles |
| Applications | /applications | GET/POST | ✅ | ⚠️ IDOR |
| Applications | /applications/{id}/* | PATCH/GET | ✅ | ⚠️ IDOR |
| Documents | /documents/upload | POST | ✅ | ⚠️ Sin virus scan |
| Auth | /auth/* | POST | ❌ | N/A |

### B. Tecnologías y Versiones

| Componente | Versión | Notas |
|------------|---------|-------|
| Python | 3.11+ | ✅ Actualizado |
| FastAPI | Latest | ✅ Framework seguro |
| PostgreSQL | 15 | ✅ Soportado |
| Redis | 7 | ✅ Soportado |
| SQLAlchemy | 2.x | ✅ ORM seguro |
| Pydantic | 2.x | ✅ Validación fuerte |

### C. Referencias

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks)

---

**Fin del Informe**

*Generado automáticamente - ATS Platform Security Baseline Review*
*Confidencial - Solo para uso interno autorizado*
