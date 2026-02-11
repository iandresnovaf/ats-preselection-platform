#!/bin/bash
# Script de instalación del proyecto (después de instalar dependencias del sistema)

echo "🚀 Instalación del ATS Preselection Platform"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no está instalado${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python detectado: $(python3 --version)${NC}"

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js no está instalado${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Node.js detectado: $(node --version)${NC}"

cd /home/andres/.openclaw/workspace/ats-platform

# Backend
echo ""
echo -e "${YELLOW}📦 Instalando Backend...${NC}"
cd backend

# Crear entorno virtual
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activar e instalar
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✓ Backend instalado${NC}"

# Frontend
echo ""
echo -e "${YELLOW}📦 Instalando Frontend...${NC}"
cd ../frontend

# Instalar dependencias
npm install

echo -e "${GREEN}✓ Frontend instalado${NC}"

# Configurar variables de entorno
echo ""
echo -e "${YELLOW}⚙️ Configurando variables de entorno...${NC}"
cd ../backend

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Archivo .env creado. Por favor edítalo con tus credenciales.${NC}"
fi

# Crear directorio de uploads
mkdir -p uploads

echo ""
echo -e "${GREEN}✅ Instalación completada!${NC}"
echo ""
echo "📋 Próximos pasos:"
echo ""
echo "1. Configurar la base de datos PostgreSQL:"
echo "   sudo -u postgres createdb ats_platform"
echo ""
echo "2. Configurar variables de entorno:"
echo "   nano backend/.env"
echo ""
echo "3. Ejecutar migraciones:"
echo "   cd backend && alembic upgrade head"
echo ""
echo "4. Iniciar en desarrollo:"
echo "   npm run dev"
echo ""
echo "5. O usar Docker Compose:"
echo "   docker-compose up -d"
echo ""
