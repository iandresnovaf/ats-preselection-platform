"""
Crear tablas de headhunting directamente con SQLAlchemy
"""
import asyncio
import sys
sys.path.append('/home/andres/.openclaw/workspace/ats-platform/backend')

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.database import Base
from app.models.core_ats import (
    HHCandidate, HHClient, HHRole, HHApplication,
    HHDocument, HHInterview, HHAssessment, HHAssessmentScore,
    HHFlag, HHAuditLog
)

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ats_platform"

async def create_tables():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        print("🛠️ Creando tablas de headhunting...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tablas creadas exitosamente!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())
