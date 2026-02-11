# 🔧 Core ATS - Technical Specification

## 📐 Arquitectura del Sistema

### Diagrama de Arquitectura High-Level

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Web App    │  │  Mobile Web  │  │   Chrome     │  │   Webhooks   │     │
│  │  (Next.js)   │  │  (Responsive)│  │  Extension   │  │  (External)  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼────────────────┼────────────────┼────────────────┼───────────────┘
          │                │                │                │
          └────────────────┴────────────────┴────────────────┘
                                   │
                                   ▼ HTTPS/WSS
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Nginx / Traefik                               │    │
│  │  • SSL Termination  • Rate Limiting  • Load Balancing  • CORS       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            APPLICATION LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     FastAPI (Python 3.11+)                           │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │    │
│  │  │  Jobs API   │ │Candidates   │ │Evaluations  │ │   Config    │   │    │
│  │  │             │ │   API       │ │   API       │ │    API      │   │    │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘   │    │
│  │         └────────────────┴───────────────┴───────────────┘          │    │
│  │                           │                                         │    │
│  │                   ┌───────┴───────┐                                 │    │
│  │                   │  Middleware   │                                 │    │
│  │                   │ • Auth (JWT)  │                                 │    │
│  │                   │ • Rate Limit  │                                 │    │
│  │                   │ • Validation  │                                 │    │
│  │                   │ • Logging     │                                 │    │
│  │                   └───────┬───────┘                                 │    │
│  │                           │                                         │    │
│  │                   ┌───────┴───────┐                                 │    │
│  │                   │    Services   │                                 │    │
│  │                   │  (Business)   │                                 │    │
│  │                   └───────┬───────┘                                 │    │
│  └───────────────────────────┼─────────────────────────────────────────┘    │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INTEGRATION LAYER                                  │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐     │
│  │     LLM       │ │    Zoho       │ │   WhatsApp    │ │    Email      │     │
│  │   OpenAI      │ │   Recruit     │ │  Business API │ │    SMTP       │     │
│  │  Anthropic    │ │   Odoo        │ │               │ │   SendGrid    │     │
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                      │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │    PostgreSQL       │  │       Redis         │  │   Celery Workers    │  │
│  │  ┌───────────────┐  │  │  ┌───────────────┐  │  │  ┌───────────────┐  │  │
│  │  │    Jobs       │  │  │  │    Cache      │  │  │  │  CV Process   │  │  │
│  │  │  Candidates   │  │  │  │   Sessions    │  │  │  │  Evaluations  │  │  │
│  │  │ Evaluations   │  │  │  │  Rate Limit   │  │  │  │ Notifications │  │  │
│  │  │    Users      │  │  │  │    Queues     │  │  │  │    Sync       │  │  │
│  │  └───────────────┘  │  │  └───────────────┘  │  │  └───────────────┘  │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Datos

### 1. Crear Oferta de Trabajo

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Frontend │────▶│  Jobs API    │────▶│ Job Service  │────▶│  PostgreSQL  │
│          │     │   (POST)     │     │              │     │              │
└──────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │  Zoho Sync   │
                                       │   (async)    │
                                       └──────────────┘
```

### 2. Agregar Candidato

```
┌──────────┐     ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│ Frontend │────▶│ Candidates   │────▶│ Candidate Service │────▶│  PostgreSQL  │
│  o Webhook    │     │   API (POST) │     │                   │     │              │
└──────────┘     └──────────────┘     └─────────┬─────────┘     └──────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    ▼                           ▼                           ▼
            ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
            │  Check Dupl. │           │CV Processing │           │ Auto-eval    │
            │              │           │   (Celery)   │           │  (Celery)    │
            └──────────────┘           └──────────────┘           └──────────────┘
```

### 3. Evaluación con IA

```
┌──────────┐     ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│ Frontend │────▶│ Evaluations  │────▶│Evaluation Service│────▶│     LLM      │
│ (o Auto) │     │   API (POST) │     │                  │     │  Provider    │
└──────────┘     └──────────────┘     └─────────┬────────┘     └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │  Parse Resp  │
                                         │ Store Result │
                                         └──────────────┘
```

### 4. Sincronización con Zoho

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Trigger    │────▶│  Zoho Sync   │────▶│ OAuth2 Auth  │────▶│   Zoho       │
│ (Job/Cand.)  │     │   Service    │     │  (Refresh)   │     │  Recruit     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                        │
                                                                        ▼
                                                                 ┌──────────────┐
                                                                 │ Update/Create│
                                                                 │   Record     │
                                                                 └──────────────┘
```

---

## 📋 Especificación de APIs

### Base URL
```
Desarrollo:  http://localhost:8000/api/v1
Producción:  https://api.ats-platform.com/api/v1
```

### Autenticación
Todas las APIs requieren Bearer Token en header:
```http
Authorization: Bearer <access_token>
```

### Respuesta Estándar
```json
{
  "success": true,
  "data": { ... },
  "message": "Operación exitosa",
  "timestamp": "2026-02-11T14:13:00Z"
}
```

### Jobs API

#### Listar Ofertas
```http
GET /jobs?page=1&page_size=20&status=active&search=developer
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Senior Developer",
      "description": "...",
      "department": "Engineering",
      "location": "Remote",
      "seniority": "Senior",
      "sector": "Technology",
      "status": "active",
      "is_active": true,
      "assigned_consultant_id": "uuid",
      "zoho_job_id": "ZJOB001",
      "created_at": "2026-02-01T10:00:00Z",
      "updated_at": "2026-02-11T08:00:00Z",
      "candidates_count": 15
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

#### Crear Oferta
```http
POST /jobs
Content-Type: application/json

{
  "title": "Senior Developer",
  "description": "Buscamos desarrollador senior...",
  "department": "Engineering",
  "location": "Remote",
  "seniority": "Senior",
  "sector": "Technology",
  "assigned_consultant_id": "uuid"
}
```

#### Obtener Oferta
```http
GET /jobs/{id}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Senior Developer",
  "description": "...",
  "department": "Engineering",
  "location": "Remote",
  "seniority": "Senior",
  "sector": "Technology",
  "status": "active",
  "is_active": true,
  "assigned_consultant": {
    "id": "uuid",
    "full_name": "Ana García",
    "email": "ana@company.com"
  },
  "zoho_job_id": "ZJOB001",
  "created_at": "2026-02-01T10:00:00Z",
  "updated_at": "2026-02-11T08:00:00Z",
  "candidates": [
    {
      "id": "uuid",
      "full_name": "Juan Pérez",
      "status": "in_review",
      "latest_score": 85.5
    }
  ]
}
```

#### Actualizar Oferta
```http
PUT /jobs/{id}
Content-Type: application/json

{
  "title": "Lead Developer",
  "status": "active"
}
```

#### Eliminar Oferta
```http
DELETE /jobs/{id}
```

---

### Candidates API

#### Listar Candidatos
```http
GET /candidates?page=1&page_size=20&job_id=uuid&status=new&search=juan
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "email": "juan@email.com",
      "phone": "+56912345678",
      "full_name": "Juan Pérez",
      "job_opening_id": "uuid",
      "job_title": "Senior Developer",
      "status": "in_review",
      "zoho_candidate_id": "ZCAND001",
      "is_duplicate": false,
      "source": "webhook",
      "created_at": "2026-02-10T15:30:00Z",
      "latest_score": 85.5,
      "latest_decision": "PROCEED"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8
}
```

#### Crear Candidato
```http
POST /candidates
Content-Type: application/json

{
  "job_opening_id": "uuid",
  "raw_data": {
    "nombre": "Juan Pérez",
    "email": "juan@email.com",
    "telefono": "+56912345678",
    "cv_text": "...",
    "experiencia": [...],
    "educacion": [...],
    "habilidades": ["Python", "React"]
  },
  "source": "manual"
}
```

#### Obtener Candidato
```http
GET /candidates/{id}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "juan@email.com",
  "phone": "+56912345678",
  "full_name": "Juan Pérez",
  "job_opening_id": "uuid",
  "job_opening": {
    "id": "uuid",
    "title": "Senior Developer"
  },
  "status": "in_review",
  "extracted_skills": ["Python", "React", "FastAPI"],
  "extracted_experience": [...],
  "extracted_education": [...],
  "raw_data": {...},
  "zoho_candidate_id": "ZCAND001",
  "is_duplicate": false,
  "duplicate_of_id": null,
  "source": "webhook",
  "created_at": "2026-02-10T15:30:00Z",
  "updated_at": "2026-02-11T10:00:00Z",
  "evaluations": [...],
  "communications": [...]
}
```

#### Actualizar Candidato
```http
PUT /candidates/{id}
Content-Type: application/json

{
  "status": "shortlisted",
  "email": "nuevo@email.com"
}
```

---

### Evaluations API

#### Listar Evaluaciones
```http
GET /evaluations?candidate_id=uuid&page=1
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "candidate_id": "uuid",
      "candidate_name": "Juan Pérez",
      "score": 85.5,
      "decision": "PROCEED",
      "strengths": ["5+ años Python", "Experiencia en startups"],
      "gaps": ["No tiene experiencia con AWS"],
      "red_flags": [],
      "evidence": "El candidato menciona 5 años...",
      "llm_provider": "openai",
      "llm_model": "gpt-4o-mini",
      "prompt_version": "v1.0",
      "hard_filters_passed": true,
      "created_at": "2026-02-11T10:00:00Z",
      "evaluation_time_ms": 2500
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

#### Crear Evaluación (Manual)
```http
POST /evaluations
Content-Type: application/json

{
  "candidate_id": "uuid",
  "prompt_override": null
}
```

La evaluación automática se ejecuta vía Celery cuando se crea un candidato.

#### Obtener Evaluación
```http
GET /evaluations/{id}
```

#### Re-generar Evaluación
```http
POST /evaluations/{id}/regenerate
Content-Type: application/json

{
  "prompt_override": "Enfócate específicamente en..."
}
```

---

## 🗄️ Modelo de Datos

### Diagrama ER

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     users       │       │  job_openings   │       │   candidates    │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ PK id (uuid)    │◄──────┤ PK id (uuid)    │◄──────┤ PK id (uuid)    │
│    email        │       │    title        │       │    email        │
│    full_name    │       │    description  │       │    phone        │
│    role         │       │    department   │       │    full_name    │
│    status       │       │    location     │       │ FK job_opening  │
│    created_at   │       │    seniority    │       │    status       │
│    updated_at   │       │    sector       │       │    raw_data     │
└─────────────────┘       │ FK assigned_to  │       │    is_duplicate │
         ▲                │    zoho_job_id  │       │    source       │
         │                │    is_active    │       │    created_at   │
         │                │    status       │       └────────┬────────┘
         │                │    created_at   │                │
         │                └─────────────────┘                │
         │                                                  │
         │                       ┌──────────────────────────┘
         │                       │
         │                ┌──────┴──────────┐
         │                │   evaluations   │
         │                ├─────────────────┤
         │                │ PK id (uuid)    │
         │                │ FK candidate_id │
         │                │    score        │
         │                │    decision     │
         │                │    strengths    │
         │                │    gaps         │
         │                │    red_flags    │
         │                │    evidence     │
         │                │    llm_provider │
         │                │    llm_model    │
         │                │    created_at   │
         │                └─────────────────┘
         │
         │         ┌─────────────────┐       ┌─────────────────┐
         │         │candidate_decisions│     │ communications  │
         │         ├─────────────────┤       ├─────────────────┤
         └─────────┤ PK id (uuid)    │       │ PK id (uuid)    │
                   │ FK candidate_id │       │ FK candidate_id │
                   │ FK consultant_id│       │    type         │
                   │    decision     │       │    status       │
                   │    notes        │       │    subject      │
                   │    synced_to_zoho│      │    body         │
                   │    created_at   │       │    sent_at      │
                   └─────────────────┘       └─────────────────┘

┌─────────────────┐
│ configurations  │
├─────────────────┤
│ PK id (uuid)    │
│    category     │
│    key          │
│    value_enc    │
│    is_encrypted │
│    updated_by   │
└─────────────────┘

┌─────────────────┐
│   audit_logs    │
├─────────────────┤
│ PK id (uuid)    │
│ FK user_id      │
│    action       │
│    entity_type  │
│    entity_id    │
│    old_values   │
│    new_values   │
│    created_at   │
└─────────────────┘
```

### Descripción de Tablas

#### users
Almacena usuarios del sistema (Super Admin y Consultores).

#### job_openings
Ofertas de trabajo creadas en el sistema. Pueden sincronizarse con Zoho.

#### candidates
Candidatos asociados a una oferta. Contiene datos extraídos del CV.

#### evaluations
Evaluaciones generadas por IA para cada candidato.

#### candidate_decisions
Decisiones manuales de los consultores sobre candidatos.

#### communications
Mensajes enviados a candidatos (email/whatsapp).

#### configurations
Configuración del sistema almacenada cifrada.

#### audit_logs
Log de auditoría para cambios importantes.

---

## 📊 Secuencia de Implementación

### Sprint 1: Fundamentos (Días 1-2)
```
Día 1:
  ├─ DB-001: Alembic setup
  ├─ DB-002: Initial migration
  └─ DB-003: Core ATS migration

Día 2:
  ├─ DB-004: Seed data
  ├─ API-001: Job models & schemas
  └─ API-002: Job service & router
```

### Sprint 2: Backend Core (Días 3-4)
```
Día 3:
  ├─ API-003: Candidates API
  ├─ API-004: Evaluations API
  └─ INT-001: LLM integration base

Día 4:
  ├─ API-005: Testing endpoints
  ├─ INT-002: Email service
  └─ INT-003: LLM prompts optimization
```

### Sprint 3: Integraciones (Días 5-6)
```
├─ INT-004: Zoho integration
├─ INT-005: WhatsApp integration
└─ INT-006: Webhook handlers
```

### Sprint 4: Frontend (Días 7-8)
```
├─ FE-001: Jobs pages
├─ FE-002: Candidates pages
├─ FE-003: Evaluations pages
└─ FE-004: Dashboard integration
```

### Sprint 5: Testing (Días 9-10)
```
├─ QA-001: Backend tests
├─ QA-002: Frontend tests
├─ QA-003: E2E tests
└─ QA-004: Performance tests
```

### Sprint 6: Deploy (Día 11)
```
├─ DEP-001: Docker production
├─ DEP-002: CI/CD pipeline
└─ DEP-003: Documentation
```

---

## 🔒 Seguridad

### Autenticación
- JWT con expiración de 15 minutos (access token)
- Refresh tokens de 7 días
- Almacenamiento en cookies httpOnly

### Autorización
- Roles: super_admin, consultant, viewer
- Permisos por recurso
- Middleware de verificación

### Datos Sensibles
- Credenciales de APIs cifradas con Fernet (AES-256)
- Contraseñas hasheadas con bcrypt
- Variables de entorno para secrets

### Headers de Seguridad
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

---

## 🚀 Performance

### Optimizaciones
- **Database:** Índices en campos de búsqueda (email, status, created_at)
- **Cache:** Redis para sesiones y rate limiting
- **Async:** Operaciones I/O no bloqueantes
- **Pagination:** Todos los listados paginados
- **N+1:** Eager loading en relaciones

### Targets
- API response time: <200ms (p95)
- Evaluación IA: <5s
- CV processing: <10s
- Database queries: <50ms

---

## 📚 Referencias

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/)
- [Next.js App Router](https://nextjs.org/docs/app)
- [OpenAI API](https://platform.openai.com/docs)

---

**Versión:** 1.0  
**Fecha:** 2026-02-11  
**Autor:** Core ATS Team
