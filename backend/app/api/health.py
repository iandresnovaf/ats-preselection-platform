from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
import redis.asyncio as redis
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Check DB
        await db.execute(text("SELECT 1"))
        
        # Check Redis
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        
        return {"status": "healthy", "services": ["database", "redis"]}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
