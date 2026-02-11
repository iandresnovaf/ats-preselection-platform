#!/bin/bash
# Script manual de instalación - Ejecutar con sudo
# Guardar como: install-deps.sh
# Ejecutar: sudo bash install-deps.sh

echo "🚀 Instalando dependencias del sistema para ATS Platform"
echo "========================================================"

# Actualizar
echo "📦 Actualizando sistema..."
apt update

# Python y herramientas
echo "🐍 Instalando Python y dependencias..."
apt install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    python3-dev \
    build-essential \
    libpq-dev \
    postgresql-client \
    redis-tools \
    curl \
    git

# Node.js 20
echo "📦 Instalando Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# GitHub CLI
echo "🔧 Instalando GitHub CLI..."
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
apt update
apt install -y gh

# Docker (opcional pero recomendado)
echo "🐳 Instalando Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker $SUDO_USER
rm get-docker.sh

# PostgreSQL
echo "🐘 Instalando PostgreSQL..."
apt install -y postgresql postgresql-contrib
systemctl enable postgresql
systemctl start postgresql

# Crear base de datos
sudo -u postgres psql -c "CREATE DATABASE ats_platform;" 2>/dev/null || echo "Base de datos ya existe"
sudo -u postgres psql -c "CREATE USER ats_user WITH PASSWORD 'ats_password';" 2>/dev/null || echo "Usuario ya existe"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ats_platform TO ats_user;"

echo ""
echo "✅ Dependencias instaladas!"
echo ""
echo "Por favor cierra y vuelve a abrir la terminal"
echo "Luego ejecuta: cd /home/andres/.openclaw/workspace/ats-platform && ./install.sh"
