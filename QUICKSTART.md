# 🚀 GUÍA RÁPIDA - Instalación Completa

## PASO 1: Instalar Dependencias del Sistema (Requiere sudo)

Abre una terminal y ejecuta:

```bash
cd /home/andres/.openclaw/workspace
sudo bash install-deps-manual.sh
```

Esto instalará:
- Python 3.12 + pip + venv
- Node.js 20
- GitHub CLI (gh)
- Docker
- PostgreSQL
- Redis

---

## PASO 2: Configurar GitHub y Subir Código

Después de cerrar y volver a abrir la terminal:

```bash
cd /home/andres/.openclaw/workspace
bash push-to-github.sh
```

Se abrirá un navegador para autenticar con GitHub.

---

## PASO 3: Instalar el Proyecto

```bash
cd /home/andres/.openclaw/workspace/ats-platform
./install.sh
```

---

## PASO 4: Configurar Variables de Entorno

```bash
cd /home/andres/.openclaw/workspace/ats-platform/backend
cp .env.example .env
nano .env
```

Edita el archivo `.env` con tus credenciales:
```env
DATABASE_URL=postgresql://ats_user:ats_password@localhost:5432/ats_platform
SECRET_KEY=genera-una-clave-larga-y-segura-aqui
DEFAULT_ADMIN_EMAIL=tu-email@ejemplo.com
DEFAULT_ADMIN_PASSWORD=tu-password-segura
```

---

## PASO 5: Ejecutar Migraciones

```bash
cd /home/andres/.openclaw/workspace/ats-platform/backend
source venv/bin/activate

# Instalar alembic si no está
pip install alembic

# Crear migración inicial
alembic init migrations

# Editar alembic.ini para configurar sqlalchemy.url
# Editar migrations/env.py para importar los modelos

# Crear migración
alembic revision --autogenerate -m "Initial migration"

# Ejecutar migración
alembic upgrade head
```

---

## PASO 6: Iniciar el Proyecto

### Opción A: Con Docker Compose (Recomendado)

```bash
cd /home/andres/.openclaw/workspace/ats-platform
docker-compose up -d
```

### Opción B: Manual

Terminal 1 - Backend:
```bash
cd /home/andres/.openclaw/workspace/ats-platform/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Terminal 2 - Frontend:
```bash
cd /home/andres/.openclaw/workspace/ats-platform/frontend
npm run dev
```

---

## 🌐 Accesos

Una vez iniciado:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/api/docs
- **Configuración**: http://localhost:3000/config

---

## 📋 Comandos Útiles

```bash
# Ver logs de Docker
docker-compose logs -f

# Detener Docker
docker-compose down

# Reiniciar servicios
docker-compose restart

# Acceder a PostgreSQL
sudo -u postgres psql ats_platform

# Acceder a Redis
redis-cli

# Ejecutar tests
pytest

# Formatear código
black app
isort app
```

---

## 🔧 Solución de Problemas

### Error: "python3-venv not found"
```bash
sudo apt install python3.12-venv
```

### Error: "permission denied"
```bash
chmod +x /home/andres/.openclaw/workspace/*.sh
chmod +x /home/andres/.openclaw/workspace/ats-platform/*.sh
```

### Error: "database does not exist"
```bash
sudo -u postgres createdb ats_platform
```

### Error: "connection refused" (PostgreSQL)
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

---

## ✅ Checklist de Instalación

- [ ] Paso 1: Dependencias del sistema instaladas
- [ ] Paso 2: Repositorio creado en GitHub
- [ ] Paso 3: Proyecto instalado (venv + npm)
- [ ] Paso 4: Variables de entorno configuradas
- [ ] Paso 5: Migraciones ejecutadas
- [ ] Paso 6: Proyecto iniciado y funcionando
- [ ] Acceso a http://localhost:3000/config

---

## 📚 Documentación

- `README.md` - Documentación general
- `SETUP.md` - Guía detallada
- `docker-compose.yml` - Configuración Docker
- `backend/.env.example` - Variables de entorno de ejemplo

---

**¡Listo para desarrollar!** 🎉

Después de completar estos pasos tendrás:
1. ✅ Código en GitHub (https://github.com/tu-usuario/ats-preselection-platform)
2. ✅ Backend Python/FastAPI corriendo
3. ✅ Frontend Next.js corriendo
4. ✅ Base de datos PostgreSQL configurada
5. ✅ Panel de configuración funcional
