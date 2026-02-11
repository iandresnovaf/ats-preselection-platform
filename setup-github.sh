#!/bin/bash
# Script para configurar GitHub CLI y crear el repositorio

echo "🚀 Configuración de GitHub Repository"
echo ""

# Verificar si gh está instalado
if ! command -v gh &> /dev/null; then
    echo "📦 Instalando GitHub CLI..."
    
    # Detectar distribución
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
        sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
        sudo apt update
        sudo apt install gh -y
    elif [ -f /etc/redhat-release ]; then
        # Fedora/RHEL
        sudo dnf install gh -y
    else
        echo "❌ Distribución no soportada para instalación automática"
        echo "Visita: https://github.com/cli/cli#installation"
        exit 1
    fi
fi

# Autenticar con GitHub
echo ""
echo "🔐 Autenticando con GitHub..."
echo "Se abrirá un navegador para autenticación."
gh auth login --web

# Verificar autenticación
if ! gh auth status &> /dev/null; then
    echo "❌ Error de autenticación"
    exit 1
fi

# Crear repositorio
echo ""
echo "📁 Creando repositorio..."
cd /home/andres/.openclaw/workspace/ats-platform

# Verificar si ya existe remoto
if git remote | grep -q "origin"; then
    echo "⚠️  El remoto 'origin' ya existe"
else
    gh repo create ats-preselection-platform \
        --public \
        --description "Plataforma de preselección automatizada de candidatos" \
        --source=. \
        --remote=origin \
        --push
fi

echo ""
echo "✅ Repositorio creado exitosamente!"
echo "URL: https://github.com/$(gh api user -q .login)/ats-preselection-platform"
