"""Servicio para gestión de clientes en RHTools."""
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.rhtools import Client
from app.schemas import ClientCreate, ClientUpdate


class ClientService:
    """Servicio para gestionar clientes en RHTools."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, client_id: str) -> Optional[Client]:
        """Obtener cliente por ID."""
        result = await self.db.execute(
            select(Client).where(
                and_(
                    Client.id == client_id,
                    Client.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def list_clients(
        self,
        status: Optional[str] = None,
        industry: Optional[str] = None,
        owner_id: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Client], int]:
        """Listar clientes con filtros y paginación."""
        query = select(Client).where(Client.is_deleted == False)
        
        # Aplicar filtros
        filters = []
        if status:
            filters.append(Client.status == status)
        if industry:
            filters.append(Client.industry == industry)
        if owner_id:
            filters.append(Client.owner_user_id == owner_id)
        if search:
            search_filter = or_(
                Client.name.ilike(f"%{search}%"),
                Client.legal_name.ilike(f"%{search}%"),
                Client.email.ilike(f"%{search}%"),
            )
            filters.append(search_filter)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Ordenar y paginar
        query = query.order_by(desc(Client.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        clients = result.scalars().all()
        
        return clients, total
    
    async def create_client(self, data: ClientCreate, created_by: Optional[str] = None) -> Client:
        """Crear nuevo cliente."""
        client = Client(
            name=data.name,
            legal_name=data.legal_name,
            tax_id=data.tax_id,
            industry=data.industry,
            sector=data.sector,
            company_size=data.company_size,
            website=data.website,
            email=data.email,
            phone=data.phone,
            address=data.address,
            city=data.city,
            country=data.country,
            owner_user_id=data.owner_user_id,
            status="active",
            settings=str(data.settings) if data.settings else None,
        )
        
        self.db.add(client)
        await self.db.flush()
        await self.db.refresh(client)
        
        return client
    
    async def update_client(
        self,
        client_id: str,
        data: ClientUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[Client]:
        """Actualizar cliente."""
        client = await self.get_by_id(client_id)
        if not client:
            return None
        
        # Actualizar campos si se proporcionan
        if data.name is not None:
            client.name = data.name
        if data.legal_name is not None:
            client.legal_name = data.legal_name
        if data.tax_id is not None:
            client.tax_id = data.tax_id
        if data.industry is not None:
            client.industry = data.industry
        if data.sector is not None:
            client.sector = data.sector
        if data.company_size is not None:
            client.company_size = data.company_size
        if data.website is not None:
            client.website = data.website
        if data.email is not None:
            client.email = data.email
        if data.phone is not None:
            client.phone = data.phone
        if data.address is not None:
            client.address = data.address
        if data.city is not None:
            client.city = data.city
        if data.country is not None:
            client.country = data.country
        if data.status is not None:
            client.status = data.status
        if data.owner_user_id is not None:
            client.owner_user_id = data.owner_user_id
        if data.settings is not None:
            client.settings = str(data.settings)
        
        client.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(client)
        
        return client
    
    async def delete_client(self, client_id: str, deleted_by: Optional[str] = None) -> bool:
        """Soft delete de cliente."""
        client = await self.get_by_id(client_id)
        if not client:
            return False
        
        client.soft_delete()
        await self.db.flush()
        
        return True
    
    async def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Obtener estadísticas de un cliente."""
        from app.models.rhtools import Submission, PipelineTemplate
        
        # Contar submissions
        submissions_result = await self.db.execute(
            select(func.count()).where(Submission.client_id == client_id)
        )
        total_submissions = submissions_result.scalar()
        
        # Contar pipelines
        pipelines_result = await self.db.execute(
            select(func.count()).where(PipelineTemplate.client_id == client_id)
        )
        total_pipelines = pipelines_result.scalar()
        
        return {
            "total_submissions": total_submissions,
            "total_pipelines": total_pipelines,
        }
