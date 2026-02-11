#!/bin/bash
# Script de instalación de dependencias del sistema (requiere sudo)

echo "🚀 Instalación de dependencias del sistema"
echo ""
echo "Este script requiere privilegios de sudo."
echo ""

# Actualizar sistema
sudo apt update

# Instalar Python y dependencias
sudo apt install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    python3-dev \
    build-essential \
    libpq-dev \
    postgresql-client

# Instalar Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Instalar GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh -y

# Instalar Docker (opcional)
if ! command -v docker &> /dev/null; then
    echo "🐳 Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

echo ""
echo "✅ Dependencias instaladas!"
echo ""
echo "Por favor cierra y vuelve a abrir la terminal para aplicar los cambios."
