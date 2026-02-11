#!/bin/bash
# Reset Database Script
# Elimina y recrea la base de datos completa (solo desarrollo)

set -e

cd "$(dirname "$0")/.."

# Verificar entorno de desarrollo
if [ "${ENV}" = "production" ] || [ "${ENV}" = "prod" ]; then
    echo "❌ ERROR: No se puede ejecutar reset en producción"
    exit 1
fi

if [ -z "${SKIP_CONFIRM}" ]; then
    echo "⚠️  ATENCIÓN: Esto eliminará TODOS los datos de la base de datos"
    read -p "¿Estás seguro? (escribe 'yes' para continuar): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "❌ Cancelado"
        exit 1
    fi
fi

echo "🗑️  Eliminando base de datos..."

# Obtener URL de la base de datos
DB_URL=$(python -c "from app.core.config import settings; print(settings.DATABASE_URL)")

# Parsear URL para obtener nombre de la base de datos
DB_NAME=$(echo "$DB_URL" | sed -E 's/.*\/([^?]+).*/\1/')

echo "   Base de datos: $DB_NAME"

# Ejecutar reset usando SQLAlchemy
python -c "
import asyncio
import sys
sys.path.append('.')

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def reset_db():
    # Crear engine a postgres (no a la DB específica)
    db_url = settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
    
    # Parsear nombre de la DB
    db_name = db_url.split('/')[-1].split('?')[0]
    
    # Conectar a postgres para drop/create
    postgres_url = db_url.rsplit('/', 1)[0] + '/postgres'
    engine = create_async_engine(postgres_url, isolation_level='AUTOCOMMIT')
    
    async with engine.connect() as conn:
        # Terminar conexiones activas
        await conn.execute(f\"\"\"
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE datname = '{db_name}' AND pid <> pg_backend_pid()
        \"\"\")
        
        # Drop y create
        await conn.execute(f'DROP DATABASE IF EXISTS \"{db_name}\"')
        await conn.execute(f'CREATE DATABASE \"{db_name}\"')
        print(f'Base de datos {db_name} recreada')
    
    await engine.dispose()

asyncio.run(reset_db())
"

echo "🔄 Ejecutando migraciones..."
alembic upgrade head

echo "🌱 Cargando datos de prueba..."
python -c "
import asyncio
import sys
sys.path.append('.')
from app.migrations.seed_data import seed_database
asyncio.run(seed_database())
"

echo "✅ Base de datos reseteada y poblada exitosamente"
