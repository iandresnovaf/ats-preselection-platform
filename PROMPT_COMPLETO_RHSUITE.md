# RH SUITE - Prompt de Desarrollo Completo v1.0

## 🎯 VISIÓN GENERAL

**RH Suite** es una plataforma de reclutamiento inteligente compuesta por dos productos:
- **RHMatch**: Motor de IA para matching de candidatos
- **RHTools**: CRM y sistema de operaciones para consultoras

---

## 🏗️ ARQUITECTURA DE PRODUCTO

### Estructura de Dos Productos Independientes

```
┌─────────────────────────────────────────────────────────────┐
│                    RH SUITE                                 │
├──────────────────────┬──────────────────────────────────────┤
│      RHMatch         │           RHTools                    │
│   (Sistema de IA)    │    (Gestión de Reclutamiento)        │
├──────────────────────┼──────────────────────────────────────┤
│ • Matching IA        │ • Gestión de Clientes                │
│ • Score 0-100        │ • Pipeline Visual (Kanban)           │
│ • Análisis de CVs    │ • Submissions de Candidatos          │
│ • Preguntas IA       │ • Documentos con OCR                 │
│ • Recomendaciones    │ • Procesamiento de CVs               │
└──────────────────────┴──────────────────────────────────────┘
           │                           │
           └───────────┬───────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
┌───▼────┐      ┌──────▼──────┐    ┌──────▼──────┐
│  Zoho  │      │    Odoo     │    │ Standalone  │
│Recruit │      │   HR Module │    │   (Sin CRM) │
└────────┘      └─────────────┘    └─────────────┘
```

**Principio clave**: RHMatch puede funcionar standalone o integrado. RHTools es opcional.

---

## 🛠️ STACK TECNOLÓGICO

### Backend
```yaml
Framework: FastAPI 0.104+
Python: 3.11+
Base de Datos: PostgreSQL 15+ (asyncpg)
Cache: Redis 7+
ORM: SQLAlchemy 2.0+ (async)
Migraciones: Alembic
Tareas Background: Celery + Redis
AI/ML: OpenAI API (GPT-4o-mini)
Documentos: pdfplumber, python-docx, pytesseract
Testing: pytest, pytest-asyncio, httpx
```

### Frontend
```yaml
Framework: Next.js 14+ (App Router)
Language: TypeScript 5+
Styling: Tailwind CSS 3+
UI Components: shadcn/ui
State Management: Zustand + TanStack Query
Forms: React Hook Form + Zod
Testing: Vitest + React Testing Library
Build: Static export para deployment simple
```

### DevOps
```yaml
Container: Docker + Docker Compose
Web Server: Nginx (reverse proxy)
SSL: Let's Encrypt (certbot)
Monitoreo: Prometheus + Grafana (opcional)
Logs: Structured JSON logging
```

---

## 📊 MODELO DE DATOS (Diseño Normalizado)

### Core Tables
```sql
-- Usuarios y Autenticación
users:
  - id: UUID PK
  - email: VARCHAR(255) UNIQUE
  - email_normalized: VARCHAR(255) INDEX
  - password_hash: VARCHAR(255)
  - full_name: VARCHAR(255)
  - role: ENUM('super_admin', 'consultant', 'viewer')
  - status: ENUM('active', 'inactive')
  - last_login: TIMESTAMP
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

-- Ofertas de Trabajo
job_openings:
  - id: UUID PK
  - title: VARCHAR(255) NOT NULL
  - description: TEXT
  - requirements: JSONB  -- {skills: [], experience_years: int, education: []}
  - department: VARCHAR(100)
  - location: VARCHAR(255)
  - seniority: VARCHAR(50)
  - sector: VARCHAR(100)
  - employment_type: ENUM('full-time', 'part-time', 'contract', 'internship')
  - salary_range_min: INTEGER
  - salary_range_max: INTEGER
  - job_description_file_id: UUID FK -> documents
  - assigned_consultant_id: UUID FK -> users
  -- Integraciones
  - zoho_job_id: VARCHAR(100)
  - external_id: VARCHAR(100)
  - source: VARCHAR(50)
  -- Estado
  - status: ENUM('draft', 'active', 'paused', 'closed')
  - is_active: BOOLEAN DEFAULT true
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

-- Candidatos
candidates:
  - id: UUID PK
  -- Datos de contacto
  - email: VARCHAR(255)
  - email_normalized: VARCHAR(255) INDEX
  - phone: VARCHAR(50)
  - phone_normalized: VARCHAR(50) INDEX
  - full_name: VARCHAR(255)
  -- Datos extraídos del CV
  - raw_data: JSONB
  - extracted_skills: JSONB
  - extracted_experience: JSONB
  - extracted_education: JSONB
  -- Relación
  - job_opening_id: UUID FK -> job_openings
  -- Estado
  - status: ENUM('new', 'screening', 'interview', 'evaluation', 'offer', 'hired', 'rejected')
  -- Integraciones
  - zoho_candidate_id: VARCHAR(100)
  - external_id: VARCHAR(100)
  - linkedin_url: VARCHAR(500)
  - source: VARCHAR(50)
  -- Anti-duplicados
  - duplicate_of_id: UUID FK -> candidates
  - is_duplicate: BOOLEAN DEFAULT false
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

-- Evaluaciones con IA
evaluations:
  - id: UUID PK
  - candidate_id: UUID FK -> candidates
  - job_opening_id: UUID FK -> job_openings
  -- Score y decisión
  - score: FLOAT  -- 0-100
  - decision: ENUM('PROCEED', 'REVIEW', 'REJECT')
  -- Detalles del match
  - match_details: JSONB  -- {skills_match: %, experience_match: %, education_match: %}
  - strengths: JSONB
  - gaps: JSONB
  - red_flags: JSONB
  - reasoning: TEXT
  -- Metadata IA
  - llm_provider: VARCHAR(50)
  - llm_model: VARCHAR(50)
  - prompt_version: VARCHAR(20)
  - tokens_used: INTEGER
  - evaluation_time_ms: INTEGER
  -- Estado
  - is_cached: BOOLEAN DEFAULT false
  - cache_expires_at: TIMESTAMP
  - created_at: TIMESTAMP

-- Resultados de Matching
match_results:
  - id: UUID PK
  - candidate_id: UUID FK -> candidates
  - job_opening_id: UUID FK -> job_openings
  - score: FLOAT NOT NULL  -- 0-100
  - match_details: JSONB
  - recommendation: ENUM('PROCEED', 'REVIEW', 'REJECT')
  - reasoning: TEXT
  - strengths: JSONB
  - gaps: JSONB
  - red_flags: JSONB
  - analysis_duration_ms: INTEGER
  - llm_provider: VARCHAR(50)
  - llm_model: VARCHAR(100)
  - analyzed_by: UUID FK -> users
  - analyzed_at: TIMESTAMP
  - is_cached: BOOLEAN DEFAULT false
  - cache_expires_at: TIMESTAMP
  - created_at: TIMESTAMP

-- Configuraciones
credentials:
  - id: UUID PK
  - category: ENUM('whatsapp', 'zoho', 'llm', 'email', 'general')
  - key: VARCHAR(100)
  - value: TEXT ENCRYPTED  -- Encriptado con Fernet
  - is_encrypted: BOOLEAN DEFAULT true
  - description: TEXT
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP
```

### RH Tools Tables
```sql
-- Clientes (empresas contratantes)
clients:
  - id: UUID PK
  - name: VARCHAR(255) NOT NULL
  - industry: VARCHAR(100)
  - website: VARCHAR(500)
  - contact_email: VARCHAR(255)
  - contact_phone: VARCHAR(50)
  - address: TEXT
  - notes: TEXT
  - is_active: BOOLEAN DEFAULT true
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

-- Submissions (candidatos enviados a clientes)
submissions:
  - id: UUID PK
  - client_id: UUID FK -> clients
  - candidate_id: UUID FK -> candidates
  - job_opening_id: UUID FK -> job_openings
  - status: ENUM('submitted', 'reviewing', 'interview', 'offer', 'accepted', 'rejected')
  - submitted_by: UUID FK -> users
  - submitted_at: TIMESTAMP
  - notes: TEXT
  - feedback: TEXT
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

-- Documentos
documents:
  - id: UUID PK
  - submission_id: UUID FK -> submissions
  - candidate_id: UUID FK -> candidates
  - client_id: UUID FK -> clients
  - original_filename: VARCHAR(500)
  - storage_filename: VARCHAR(500) UNIQUE
  - file_path: VARCHAR(1000)
  - file_size: INTEGER
  - mime_type: VARCHAR(100)
  - document_type: ENUM('resume', 'cover_letter', 'portfolio', 'contract', 'offer_letter', 'interview_notes', 'evaluation', 'other')
  - status: ENUM('pending', 'processing', 'processed', 'error')
  - is_private: BOOLEAN DEFAULT false
  - uploaded_by: UUID FK -> users
  - created_at: TIMESTAMP
  - updated_at: TIMESTAMP

-- Pipeline Stages (para kanban)
pipeline_stages:
  - id: UUID PK
  - name: VARCHAR(100) NOT NULL
  - order: INTEGER
  - color: VARCHAR(20)
  - is_default: BOOLEAN DEFAULT false
  - created_at: TIMESTAMP

-- Pipeline Items (candidatos en el pipeline)
pipeline_items:
  - id: UUID PK
  - candidate_id: UUID FK -> candidates
  - stage_id: UUID FK -> pipeline_stages
  - job_opening_id: UUID FK -> job_openings
  - assigned_to: UUID FK -> users
  - notes: TEXT
  - moved_at: TIMESTAMP
  - created_at: TIMESTAMP
```

---

## 🔌 API ENDPOINTS (Diseño RESTful)

### Autenticación
```
POST   /api/v1/auth/login              # Login con email/password
POST   /api/v1/auth/logout             # Logout
GET    /api/v1/auth/me                 # Obtener usuario actual
POST   /api/v1/auth/refresh            # Refresh token
POST   /api/v1/auth/forgot-password    # Solicitar reset
POST   /api/v1/auth/reset-password     # Reset con token
POST   /api/v1/auth/change-password    # Cambiar password (autenticado)
POST   /api/v1/auth/change-email       # Cambiar email (autenticado)
```

### Usuarios
```
GET    /api/v1/users                   # Listar usuarios (paginado)
GET    /api/v1/users/{id}              # Obtener usuario
POST   /api/v1/users                   # Crear usuario
PATCH  /api/v1/users/{id}              # Actualizar usuario
DELETE /api/v1/users/{id}              # Desactivar usuario
POST   /api/v1/users/{id}/activate     # Activar usuario
POST   /api/v1/users/{id}/deactivate   # Desactivar usuario
```

### Jobs (Ofertas)
```
GET    /api/v1/jobs                    # Listar jobs
GET    /api/v1/jobs/{id}               # Obtener job
POST   /api/v1/jobs                    # Crear job
PATCH  /api/v1/jobs/{id}               # Actualizar job
DELETE /api/v1/jobs/{id}               # Eliminar job (soft delete)
POST   /api/v1/jobs/{id}/upload-description  # Subir PDF de JD
POST   /api/v1/jobs/{id}/close         # Cerrar job
POST   /api/v1/jobs/{id}/pause         # Pausar job
POST   /api/v1/jobs/{id}/activate      # Reactivar job
GET    /api/v1/jobs/{id}/candidates    # Candidatos de un job
GET    /api/v1/jobs/{id}/statistics    # Estadísticas del job
```

### Candidatos
```
GET    /api/v1/candidates              # Listar candidatos
GET    /api/v1/candidates/{id}         # Obtener candidato
POST   /api/v1/candidates              # Crear candidato manual
POST   /api/v1/candidates/upload-cv    # Crear desde CV (PDF/DOCX)
PATCH  /api/v1/candidates/{id}         # Actualizar candidato
DELETE /api/v1/candidates/{id}         # Eliminar candidato
POST   /api/v1/candidates/{id}/evaluate # Evaluar con IA
POST   /api/v1/candidates/{id}/change-status  # Cambiar estado
GET    /api/v1/candidates/{id}/evaluations    # Evaluaciones del candidato
POST   /api/v1/candidates/{id}/upload-cv      # Subir CV
```

### Matching IA
```
POST   /api/v1/matching/analyze        # Analizar match candidato-job
GET    /api/v1/matching/candidate/{id}/jobs   # Mejores jobs para candidato
GET    /api/v1/matching/job/{id}/candidates  # Mejores candidatos para job
POST   /api/v1/matching/batch          # Análisis batch
GET    /api/v1/matching/top/{job_id}   # Top N matches
POST   /api/v1/matching/{id}/questions # Generar preguntas de entrevista
```

### RH Tools - Clientes
```
GET    /api/v1/rhtools/clients         # Listar clientes
GET    /api/v1/rhtools/clients/{id}    # Obtener cliente
POST   /api/v1/rhtools/clients         # Crear cliente
PATCH  /api/v1/rhtools/clients/{id}    # Actualizar cliente
DELETE /api/v1/rhtools/clients/{id}    # Eliminar cliente
```

### RH Tools - Submissions
```
GET    /api/v1/rhtools/submissions     # Listar submissions
POST   /api/v1/rhtools/submissions     # Crear submission
PATCH  /api/v1/rhtools/submissions/{id} # Actualizar submission
```

### RH Tools - Pipeline
```
GET    /api/v1/rhtools/pipeline/stages # Listar stages
GET    /api/v1/rhtools/pipeline        # Kanban completo
PATCH  /api/v1/rhtools/pipeline/{id}   # Mover candidato entre stages
```

### Documentos
```
GET    /api/v1/documents               # Listar documentos
POST   /api/v1/documents               # Subir documento
GET    /api/v1/documents/{id}          # Descargar documento
DELETE /api/v1/documents/{id}          # Eliminar documento
POST   /api/v1/documents/{id}/parse    # Parsear documento con OCR
```

### Configuración
```
GET    /api/v1/config/status           # Estado de configuraciones
GET    /api/v1/config/{category}       # Obtener config
POST   /api/v1/config/{category}       # Guardar config
POST   /api/v1/config/{category}/test  # Testear conexión
```

---

## 🔒 SEGURIDAD (Implementar desde Día 1)

### Autenticación
- JWT con access tokens (30 min) + refresh tokens (7 días)
- Cookies httpOnly, Secure, SameSite=Strict
- Protección contra timing attacks (dummy hash)
- Rate limiting: 5 intentos/min en login

### Autorización
- RBAC con 3 roles: super_admin, consultant, viewer
- Middleware de permisos en cada endpoint
- Verificar ownership de recursos

### Datos Sensibles
- Contraseñas: bcrypt con 12 rounds
- API Keys: Fernet (AES-256) en base de datos
- Variables de entorno para secrets
- Validación de inputs con Pydantic schemas

### Headers de Seguridad
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 🎨 FRONTEND - ESTRUCTURA

### Layout Principal
```
┌─────────────────────────────────────────┐
│  Navbar (Logo + Menu + User Dropdown)   │
├──────────┬──────────────────────────────┤
│          │                              │
│ Sidebar  │      Main Content            │
│          │      (Pages)                 │
│ (Menu)   │                              │
│          │                              │
└──────────┴──────────────────────────────┘
```

### Rutas Principales
```
/                      → Landing
/login                 → Login
/forgot-password       → Recuperar password
/reset-password        → Reset con token
/dashboard             → Dashboard
/dashboard/jobs        → Lista de ofertas
/dashboard/jobs/new    → Crear oferta
/dashboard/jobs/[id]   → Detalle de oferta
/dashboard/candidates  → Lista de candidatos
/dashboard/matching    → Matching IA
/dashboard/rhtools/clients      → Clientes
/dashboard/rhtools/pipeline     → Pipeline Kanban
/dashboard/rhtools/submissions  → Submissions
/dashboard/users       → Usuarios (solo admin)
/config                → Configuración
```

### Componentes Clave
- **JobForm**: Crear/editar ofertas con upload de PDF
- **CandidateForm**: Crear candidatos manual o desde CV
- **MatchingPanel**: Visualización de scores 0-100
- **InterviewQuestions**: Generador de preguntas IA
- **PipelineKanban**: Drag & drop de candidatos
- **ClientCard**: Tarjetas de clientes
- **SubmissionForm**: Enviar candidatos a clientes

---

## 🧪 TESTING ESTRATEGIA

### Backend
```
Unit Tests: pytest
  → Services (lógica de negocio)
  → Models (validaciones)
  → Utils (funciones puras)

Integration Tests: pytest-asyncio
  → API endpoints
  → Database queries
  → Cache operations

E2E Tests:
  → Flujo completo: Login → Crear Job → Subir CV → Matching
  → Integraciones externas (mocks)
```

### Frontend
```
Unit Tests: Vitest
  → Components (renderizado)
  → Hooks (lógica)
  → Utils (funciones)

Integration Tests:
  → Flujos de usuario
  → Form submissions
  → API interactions
```

### Cobertura Mínima: 70%

---

## 🚀 DEPLOYMENT

### Docker Compose
```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ats_platform
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:${DB_PASSWORD}@postgres/ats_platform
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
```

### Variables de Entorno Requeridas
```bash
# Base de datos
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/ats_platform
REDIS_URL=redis://localhost:6379/0

# Seguridad
SECRET_KEY=32-char-random-string-here
ENCRYPTION_KEY=32-byte-base64-key

# Default Admin
DEFAULT_ADMIN_EMAIL=admin@company.com
DEFAULT_ADMIN_PASSWORD=ChangeMe123!

# OpenAI
OPENAI_API_KEY=sk-...

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Environment
ENVIRONMENT=production  # or development
```

---

## ⚠️ LEARNINGS - ERRORES A EVITAR

### Base de Datos
1. ✅ **Migraciones**: Usar Alembic desde el día 1
2. ✅ **Índices**: Crear índices en campos de búsqueda frecuente
3. ✅ **Constraints**: Usar constraints UNIQUE para anti-duplicados
4. ❌ **Evitar**: Cambiar modelos sin migraciones

### Backend
1. ✅ **Type Hints**: Usar en TODAS las funciones
2. ✅ **Docstrings**: Documentar todas las clases y métodos públicos
3. ✅ **Manejo de Errores**: Usar excepciones custom, no retornar dicts
4. ✅ **Async**: Todas las operaciones I/O deben ser async
5. ❌ **Evitar**: Import circulares, usar imports locales si es necesario

### Frontend
1. ✅ **TypeScript**: Strict mode activado
2. ✅ **Manejo de Errores**: Convertir SIEMPRE errores a string antes de mostrar
3. ✅ **Loading States**: Siempre mostrar estado de carga
4. ✅ **Validación**: Zod para forms, validación en tiempo real
5. ❌ **Evitar**: `any` types, usar interfaces bien definidas

### Seguridad
1. ✅ **NUNCA**: Hardcodear secrets
2. ✅ **NUNCA**: Loguear passwords o tokens
3. ✅ **SIEMPRE**: Validar inputs en backend (nunca confiar en frontend)
4. ✅ **SIEMPRE**: Sanitizar datos antes de mostrarlos (XSS protection)

### Performance
1. ✅ **Cache**: Implementar cache para llamadas a IA (ahorro de costos)
2. ✅ **Rate Limiting**: Limitar endpoints de IA (evitar costos excesivos)
3. ✅ **Paginación**: SIEMPRE paginar listados grandes
4. ✅ **Lazy Loading**: Cargar componentes pesados bajo demanda

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### Fase 1: Core (Semana 1)
- [ ] Setup proyecto (backend + frontend)
- [ ] Base de datos con migraciones
- [ ] Autenticación JWT completa
- [ ] CRUD de Usuarios
- [ ] CRUD de Jobs
- [ ] CRUD de Candidatos

### Fase 2: IA (Semana 2)
- [ ] Integración OpenAI
- [ ] Servicio de Matching
- [ ] Endpoints de Matching
- [ ] UI de Matching
- [ ] Cache de resultados

### Fase 3: RH Tools (Semana 3)
- [ ] CRUD de Clientes
- [ ] Pipeline Kanban
- [ ] Submissions
- [ ] Documentos con OCR

### Fase 4: Integraciones (Semana 4)
- [ ] Zoho Recruit
- [ ] Odoo HR
- [ ] LinkedIn

### Fase 5: Testing & Deploy (Semana 5)
- [ ] Tests unitarios (>70% coverage)
- [ ] Tests E2E críticos
- [ ] Docker compose completo
- [ ] Deploy a producción

---

**NOTA FINAL**: Este prompt es la especificación completa. Seguirlo al pie de la letra garantiza un sistema robusto, escalable y mantenible.
