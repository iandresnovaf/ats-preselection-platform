#!/bin/bash
# Seed Data Script
# Carga datos de prueba en la base de datos (solo desarrollo)

set -e

cd "$(dirname "$0")/.."

echo "🌱 Cargando datos de prueba..."

# Verificar entorno de desarrollo
if [ "${ENV}" = "production" ] || [ "${ENV}" = "prod" ]; then
    echo "❌ ERROR: No se puede ejecutar seed en producción"
    exit 1
fi

# Ejecutar script de seed
python -c "
import asyncio
import sys
sys.path.append('.')
from app.migrations.seed_data import seed_database
asyncio.run(seed_database())
"

echo "✅ Datos de prueba cargados exitosamente"
