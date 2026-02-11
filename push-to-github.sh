#!/bin/bash
# Crear repositorio en GitHub y subir código
# Ejecutar DESPUÉS de instalar gh (GitHub CLI)

echo "🔐 Configurando GitHub..."
echo ""

# Verificar gh
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI no está instalado"
    echo "Ejecuta primero: sudo bash install-deps-manual.sh"
    exit 1
fi

# Autenticar
echo "Abriendo navegador para autenticación..."
gh auth login --web

# Verificar autenticación
if ! gh auth status &> /dev/null; then
    echo "❌ Error de autenticación"
    exit 1
fi

echo "✅ Autenticado con GitHub"
echo ""

# Crear repositorio
cd /home/andres/.openclaw/workspace/ats-platform

USERNAME=$(gh api user -q .login)
REPO_NAME="ats-preselection-platform"

echo "📁 Creando repositorio: $REPO_NAME"
echo "Usuario: $USERNAME"
echo ""

# Crear repo en GitHub
gh repo create "$REPO_NAME" \
    --public \
    --description "Plataforma de preselección automatizada de candidatos con Python/FastAPI y Next.js" \
    --source=. \
    --remote=origin \
    --push

echo ""
echo "✅ Repositorio creado y código subido!"
echo ""
echo "🔗 URL: https://github.com/$USERNAME/$REPO_NAME"
echo ""
