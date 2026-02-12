"""Dependencias específicas de RHTools."""
from fastapi import HTTPException, status
from app.core.rhtools_config import is_rhtools_enabled


async def require_rhtools_enabled():
    """
    Dependency para verificar que RHTools esté habilitado.
    
    Raises:
        HTTPException: 403 si RHTools no está habilitado
    """
    if not await is_rhtools_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Módulo RHTools no habilitado. Configure el ATS provider como 'rhtools'.",
        )
