# ATS Preselection Platform

Plataforma de preselección automatizada de candidatos para Top Management.

> **Versión Actual**: v1.1.0 - [Ver Release Notes](RELEASE_v1.1.0.md)
> 
> 🎯 **Estado**: 85% Completo - Listo para producción
> 
> 🔐 **Seguridad**: A+ (95/100) | ⚡ **Performance**: B+ (85/100)

## 🚀 Características

### Core (v1.0.0)
- **Autenticación JWT** con roles (Super Admin, Consultor, Viewer)
- **Gestión de Ofertas** de trabajo (Job Openings)
- **Ingesta de CVs** vía webhook y cron jobs
- **Evaluación con IA** (scoring 0-100%)
- **Integración Zoho Recruit** (sync bidireccional)
- **Comunicación** vía WhatsApp Business API y Email
- **Anti-duplicados** por email/teléfono
- **Landing pages** para candidatos con tokens
- **Panel de configuración** para APIs

### Nuevo: Sistema de Matching IA (v1.1.0) 🤖
- **Matching CV-to-Job** con OpenAI GPT-4o-mini
- **Score de match** 0-100 con breakdown detallado:
  - Skills match (%)
  - Experience match (%)  
  - Education match (%)
- **Recomendaciones automáticas**: PROCEED (>75) / REVIEW (50-75) / REJECT (<50)
- **Fortalezas y Gaps** identificados automáticamente
- **Preguntas de entrevista** generadas por IA (3-15 personalizadas)
- **Upload de PDF** para Job Description
- **Requirements extendidos**: skills, experiencia, educación, salario
- **Vista comparativa** Job vs Candidatos ordenados por score
- **Cache inteligente** (24h) - ahorro ~80% en costos de IA
- **Rate limiting** por usuario (evita costos excesivos)

### RH Tools (v1.1.0)
- **Gestión de Clientes** (empresas)
- **Pipeline de reclutamiento** visual (Kanban)
- **Submissions** de candidatos a clientes
- **Documentos** con OCR (PDF, DOCX, imágenes)
- **Procesamiento de CVs** automático

## 🛠️ Stack Tecnológico

### Backend
- **Python 3.11+**
- **FastAPI** - Framework web async
- **SQLAlchemy 2.0** - ORM async
- **PostgreSQL** - Base de datos
- **Redis** - Cache y colas
- **Celery** - Tareas en background
- **Alembic** - Migraciones
- **OpenAI** - Evaluación con LLM

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Tipado estático
- **Tailwind CSS** - Estilos
- **shadcn/ui** - Componentes UI
- **TanStack Query** - State management

## 📁 Estructura del Proyecto

```
ats-platform/
├── backend/
│   ├── app/
│   │   ├── api/              # Endpoints REST
│   │   ├── core/             # Config, auth, seguridad
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Lógica de negocio
│   │   ├── integrations/     # Zoho, WhatsApp, LLM
│   │   └── main.py
│   ├── alembic/              # Migraciones
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router
│   │   ├── components/       # React components
│   │   └── services/         # API clients
│   └── package.json
└── docker-compose.yml
```

## 🚀 Instalación Rápida

### Requisitos
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+

### 1. Clonar y entrar al proyecto
```bash
git clone https://github.com/andresnova/ats-preselection-platform.git
cd ats-preselection-platform
```

### 2. Instalar dependencias
```bash
npm run install:all
```

### 3. Configurar variables de entorno
```bash
cp backend/.env.example backend/.env
# Editar backend/.env con tus credenciales
```

### 4. Crear base de datos
```bash
# PostgreSQL
createdb ats_platform

# Ejecutar migraciones
cd backend
alembic upgrade head
```

### 5. Iniciar en desarrollo
```bash
npm run dev
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/api/docs

## ⚙️ Configuración

### Variables de Entorno (.env)
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ats_platform
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here-min-32-chars-long
ENCRYPTION_KEY=your-32-byte-encryption-key

# Default Admin
DEFAULT_ADMIN_EMAIL=admin@topmanagement.com
DEFAULT_ADMIN_PASSWORD=secure-password

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Configuración de Integraciones

Accede a `/config` en el frontend para configurar:

1. **WhatsApp Business API**
   - Access Token de Meta
   - Phone Number ID
   - Verify Token para webhooks

2. **Zoho Recruit**
   - Client ID / Client Secret
   - Refresh Token (OAuth2)

3. **LLM (OpenAI/Anthropic)**
   - API Key
   - Modelo (gpt-4o-mini recomendado)

4. **Email (SMTP)**
   - Host, puerto, credenciales
   - Remitente por defecto

## 🧪 Testing & Calidad

### Tests Implementados
```bash
# Backend
pytest                    # Tests unitarios y de integración
pytest tests/test_e2e_critical.py  # Tests E2E críticos

# Frontend
npm run test             # Tests de componentes
```

### Cobertura
- **Tests Unitarios**: Servicios, modelos, utilidades
- **Tests E2E**: Flujos críticos (Job → CV → Match → Score)
- **Tests de Integración**: Zoho, Odoo, LinkedIn (preparados)
- **Tests de Componentes**: JobForm, MatchingPanel, FileUpload

### Auditorías Realizadas
- ✅ **Seguridad**: A+ (95/100) - Ver [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md)
- ✅ **Best Practices**: B+ (87/100) - Ver [BEST_PRACTICES_REPORT.md](BEST_PRACTICES_REPORT.md)
- ✅ **Performance Backend**: Optimizado
- ✅ **Performance Frontend**: B+ (85/100) - Ver [PERFORMANCE_REPORT_FRONTEND.md](PERFORMANCE_REPORT_FRONTEND.md)
- ✅ **QA**: Aprobado para producción - Ver [QA_REPORT.md](QA_REPORT.md)

## 📝 API Documentation

Documentación automática generada por FastAPI:
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`

## 🔒 Seguridad

- ✅ **Auditoría de seguridad**: A+ (95/100)
- JWT tokens con expiración (access: 30min, refresh: 7días)
- Cookies httpOnly, Secure, SameSite=Strict
- Contraseñas hasheadas con bcrypt (12 rounds)
- Credenciales de APIs cifradas con Fernet (AES-256)
- CORS configurado con orígenes explícitos
- Rate limiting en endpoints sensibles (auth: 5 req/min)
- Rate limiting específico para LLM (evita costos excesivos)
- Headers de seguridad: HSTS, CSP, X-Frame-Options
- Protección contra: SQL Injection, XSS, CSRF, Timing Attacks
- Validación de inputs con Pydantic schemas
- Logs de auditoría de seguridad (login, cambios, configuraciones)

Ver reporte completo: [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md)

## 📄 Licencia

Privado - Propiedad de Top Management

## 👥 Autor

Andrés Nova - Gerente de Tecnología e Innovación
