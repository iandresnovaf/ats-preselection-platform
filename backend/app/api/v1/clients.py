"""
Core ATS API - HHClients Router
Endpoints para gestión de clientes.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core_ats import HHClient, HHRole
from app.schemas.core_ats import (
    ClientCreate, ClientUpdate, ClientResponse,
    ClientListResponse, ClientWithRolesResponse, RoleSummaryResponse
)

router = APIRouter(prefix="/clients", tags=["HHClients"])


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crear un nuevo cliente."""
    import uuid
    from datetime import datetime
    
    db_client = HHClient(
        client_id=uuid.uuid4(),
        client_name=client.client_name,
        industry=client.industry,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


@router.get("", response_model=ClientListResponse)
def list_clients(
    search: Optional[str] = Query(None, description="Buscar por nombre o industria"),
    industry: Optional[str] = Query(None, description="Filtrar por industria"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar clientes con paginación y filtros."""
    query = db.query(HHClient)
    
    if search:
        query = query.filter(HHClient.client_name.ilike(f"%{search}%"))
    
    if industry:
        query = query.filter(HHClient.industry.ilike(f"%{industry}%"))
    
    total = query.count()
    clients = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return ClientListResponse(
        items=[ClientResponse.model_validate(c) for c in clients],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener un cliente por ID."""
    client = db.query(HHClient).filter(HHClient.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: UUID,
    client_update: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Actualizar un cliente."""
    db_client = db.query(HHClient).filter(HHClient.client_id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    update_data = client_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_client, field, value)
    
    db.commit()
    db.refresh(db_client)
    return db_client
