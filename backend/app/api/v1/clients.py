"""
Core ATS API - HHClients Router
Endpoints para gestión de clientes.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core_ats import HHClient, HHRole
from app.schemas.core_ats import (
    ClientCreate, ClientUpdate, ClientResponse,
    ClientListResponse, ClientWithRolesResponse, RoleSummaryResponse
)

router = APIRouter(prefix="/clients", tags=["HHClients"])


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crear un nuevo cliente."""
    import uuid
    from datetime import datetime
    
    # Verificar que no exista un cliente con el mismo nombre
    existing = await db.execute(
        select(HHClient).where(
            func.lower(HHClient.client_name) == func.lower(client.client_name)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un cliente con el nombre '{client.client_name}'"
        )
    
    db_client = HHClient(
        client_id=uuid.uuid4(),
        client_name=client.client_name,
        industry=client.industry,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_client)
    await db.commit()
    await db.refresh(db_client)
    return db_client


@router.get("", response_model=ClientListResponse)
async def list_clients(
    search: Optional[str] = Query(None, description="Buscar por nombre o industria"),
    industry: Optional[str] = Query(None, description="Filtrar por industria"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar clientes con paginación y filtros."""
    query = select(HHClient)
    
    if search:
        query = query.where(HHClient.client_name.ilike(f"%{search}%"))
    
    if industry:
        query = query.where(HHClient.industry.ilike(f"%{industry}%"))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    clients = result.scalars().all()
    
    return ClientListResponse(
        items=[ClientResponse.model_validate(c) for c in clients],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener un cliente por ID."""
    result = await db.execute(
        select(HHClient).where(HHClient.client_id == client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    client_update: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Actualizar un cliente."""
    result = await db.execute(
        select(HHClient).where(HHClient.client_id == client_id)
    )
    db_client = result.scalar_one_or_none()
    if not db_client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Verificar nombre único si se está actualizando
    if client_update.client_name and client_update.client_name != db_client.client_name:
        existing = await db.execute(
            select(HHClient).where(
                func.lower(HHClient.client_name) == func.lower(client_update.client_name),
                HHClient.client_id != client_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un cliente con el nombre '{client_update.client_name}'"
            )
    
    update_data = client_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_client, field, value)
    
    await db.commit()
    await db.refresh(db_client)
    return db_client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Eliminar un cliente solo si no tiene vacantes asociadas."""
    # Verificar que el cliente existe
    result = await db.execute(
        select(HHClient).where(HHClient.client_id == client_id)
    )
    db_client = result.scalar_one_or_none()
    if not db_client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Verificar si tiene vacantes/roles asociados
    roles_count_result = await db.execute(
        select(func.count()).where(HHRole.client_id == client_id)
    )
    roles_count = roles_count_result.scalar()
    
    if roles_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede eliminar el cliente porque tiene {roles_count} vacante(s) asociada(s)"
        )
    
    await db.delete(db_client)
    await db.commit()
    return None
