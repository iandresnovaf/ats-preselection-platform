#!/bin/bash
# Migration Script
# Ejecuta las migraciones pendientes de Alembic

set -e

cd "$(dirname "$0")/.."

echo "🔄 Ejecutando migraciones..."

# Verificar conexión a la base de datos
echo "   Verificando conexión..."
python -c "
import asyncio
import sys
sys.path.append('.')

from app.core.database import engine

async def check_connection():
    try:
        async with engine.connect() as conn:
            result = await conn.execute('SELECT 1')
            print('   ✅ Conexión exitosa')
    except Exception as e:
        print(f'   ❌ Error de conexión: {e}')
        sys.exit(1)
    finally:
        await engine.dispose()

asyncio.run(check_connection())
"

# Mostrar versión actual
echo ""
echo "   Versión actual:"
alembic current || true

# Ejecutar migraciones
echo ""
echo "   Aplicando migraciones..."
alembic upgrade head

# Mostrar nueva versión
echo ""
echo "   Nueva versión:"
alembic current

echo ""
echo "✅ Migraciones completadas exitosamente"
