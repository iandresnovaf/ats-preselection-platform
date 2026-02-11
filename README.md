# ATS Preselection Platform

Plataforma de preselección automatizada de candidatos para Top Management.

## 🚀 Características

- **Autenticación JWT** con roles (Super Admin, Consultor)
- **Gestión de Ofertas** de trabajo (Job Openings)
- **Ingesta de CVs** vía webhook y cron jobs
- **Evaluación con IA** (scoring 0-100%)
- **Integración Zoho Recruit** (sync bidireccional)
- **Comunicación** vía WhatsApp Business API y Email
- **Anti-duplicados** por email/teléfono
- **Landing pages** para candidatos con tokens
- **Panel de configuración** para APIs

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

## 🧪 Testing

```bash
# Backend
pytest

# Frontend
npm run test
```

## 📝 API Documentation

Documentación automática generada por FastAPI:
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`

## 🔒 Seguridad

- JWT tokens con expiración
- Contraseñas hasheadas con bcrypt
- Credenciales de APIs cifradas con Fernet (AES-256)
- CORS configurado
- Rate limiting en endpoints sensibles

## 📄 Licencia

Privado - Propiedad de Top Management

## 👥 Autor

Andrés Nova - Gerente de Tecnología e Innovación
