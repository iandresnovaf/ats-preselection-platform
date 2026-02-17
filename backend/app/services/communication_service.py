"""Servicio de Comunicaciones con candidatos."""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication import (
    Communication,
    CommunicationChannel,
    CommunicationDirection,
    CommunicationMessageType,
    CommunicationStatus,
    InterestStatus
)
from app.services.whatsapp_service import WhatsAppService
from app.core.config import settings

logger = logging.getLogger(__name__)


class CommunicationService:
    """Servicio para gestionar comunicaciones con candidatos."""
    
    def __init__(self, db: AsyncSession):
        """Inicializa el servicio.
        
        Args:
            db: Sesión de base de datos
        """
        self.db = db
        self.whatsapp_service: Optional[WhatsAppService] = None
    
    async def _get_whatsapp_service(self) -> WhatsAppService:
        """Obtiene o crea el servicio de WhatsApp."""
        if self.whatsapp_service is None:
            self.whatsapp_service = WhatsAppService()
        return self.whatsapp_service
    
    async def send_whatsapp_message(
        self,
        application_id: UUID,
        candidate_id: UUID,
        to_phone: str,
        template_name: str,
        template_variables: Optional[List[str]] = None,
        message_type: CommunicationMessageType = CommunicationMessageType.INITIAL,
        created_by: Optional[UUID] = None
    ) -> Communication:
        """Envía un mensaje de WhatsApp usando template.
        
        Args:
            application_id: ID de la aplicación
            candidate_id: ID del candidato
            to_phone: Número de teléfono
            template_name: Nombre del template
            template_variables: Variables para el template
            message_type: Tipo de mensaje
            created_by: ID del usuario que envía
            
        Returns:
            Objeto Communication creado
        """
        # Validar que WhatsApp esté habilitado o en modo mock
        if not settings.WHATSAPP_ENABLED and not settings.WHATSAPP_MOCK_MODE:
            raise ValueError("WhatsApp no está habilitado. Configure WHATSAPP_ENABLED=True")
        
        # Preparar componentes del template
        components = None
        if template_variables:
            components = [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(var)}
                    for var in template_variables
                ]
            }]
        
        # Crear registro de comunicación (estado PENDING)
        content = f"Template: {template_name}"
        if template_variables:
            content += f" | Variables: {', '.join(str(v) for v in template_variables)}"
        
        comm = Communication(
            application_id=application_id,
            candidate_id=candidate_id,
            channel=CommunicationChannel.WHATSAPP,
            direction=CommunicationDirection.OUTBOUND,
            message_type=message_type,
            template_id=template_name,
            content=content,
            recipient_phone=to_phone,
            status=CommunicationStatus.PENDING,
            variables={"template_variables": template_variables or []},
            created_by=created_by
        )
        
        self.db.add(comm)
        await self.db.commit()
        await self.db.refresh(comm)
        
        # Enviar mensaje vía WhatsApp API
        try:
            whatsapp = await self._get_whatsapp_service()
            result = await whatsapp.send_template_message(
                to_phone=to_phone,
                template_name=template_name,
                components=components
            )
            
            if result.get("success"):
                comm.status = CommunicationStatus.SENT
                comm.whatsapp_message_id = result.get("message_id")
                comm.sent_at = datetime.utcnow()
                
                # Si es modo mock, marcar como delivered/read inmediatamente
                if result.get("mock"):
                    comm.status = CommunicationStatus.READ
                    comm.delivered_at = datetime.utcnow()
                    comm.read_at = datetime.utcnow()
            else:
                comm.status = CommunicationStatus.FAILED
                comm.error_message = result.get("error")
                comm.error_code = str(result.get("error_code"))
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error enviando mensaje WhatsApp: {e}")
            comm.status = CommunicationStatus.FAILED
            comm.error_message = str(e)
            await self.db.commit()
        
        return comm
    
    async def retry_failed_message(
        self,
        communication_id: UUID
    ) -> Communication:
        """Reintenta enviar un mensaje fallido.
        
        Args:
            communication_id: ID de la comunicación fallida
            
        Returns:
            Comunicación actualizada
        """
        # Obtener la comunicación
        result = await self.db.execute(
            select(Communication).where(Communication.communication_id == communication_id)
        )
        comm = result.scalar_one_or_none()
        
        if not comm:
            raise ValueError(f"Comunicación no encontrada: {communication_id}")
        
        if comm.status != CommunicationStatus.FAILED:
            raise ValueError(f"Solo se pueden reintentar mensajes fallidos. Estado actual: {comm.status}")
        
        if comm.retry_count >= 3:
            raise ValueError("Máximo de reintentos alcanzado (3)")
        
        # Incrementar contador de reintentos
        comm.retry_count += 1
        comm.status = CommunicationStatus.PENDING
        await self.db.commit()
        
        # Reintentar envío
        try:
            whatsapp = await self._get_whatsapp_service()
            
            # Preparar componentes
            components = None
            if comm.variables and comm.variables.get("template_variables"):
                components = [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(var)}
                        for var in comm.variables["template_variables"]
                    ]
                }]
            
            result = await whatsapp.send_template_message(
                to_phone=comm.recipient_phone,
                template_name=comm.template_id,
                components=components
            )
            
            if result.get("success"):
                comm.status = CommunicationStatus.SENT
                comm.whatsapp_message_id = result.get("message_id")
                comm.sent_at = datetime.utcnow()
                comm.error_message = None
                comm.error_code = None
            else:
                comm.status = CommunicationStatus.FAILED
                comm.error_message = result.get("error")
                comm.error_code = str(result.get("error_code"))
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error en reintento: {e}")
            comm.status = CommunicationStatus.FAILED
            comm.error_message = str(e)
            await self.db.commit()
        
        return comm
    
    async def record_inbound_message(
        self,
        from_phone: str,
        whatsapp_message_id: str,
        content: str,
        interest_status: str = "unknown",
        metadata: Optional[Dict] = None
    ) -> Optional[Communication]:
        """Registra un mensaje entrante del candidato.
        
        Args:
            from_phone: Número de teléfono del remitente
            whatsapp_message_id: ID del mensaje de WhatsApp
            content: Contenido del mensaje
            interest_status: Estado de interés analizado
            metadata: Metadata adicional
            
        Returns:
            Comunicación creada o None si no se encuentra candidato
        """
        # Buscar candidato por teléfono
        from app.models.core_ats import HHCandidate
        
        result = await self.db.execute(
            select(HHCandidate).where(
                or_(
                    HHCandidate.phone == from_phone,
                    HHCandidate.phone.like(f"%{from_phone}"),
                    HHCandidate.phone.like(f"{from_phone}%")
                )
            )
        )
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            logger.warning(f"No se encontró candidato para teléfono: {from_phone}")
            # Crear comunicación sin candidato asociado
            comm = Communication(
                channel=CommunicationChannel.WHATSAPP,
                direction=CommunicationDirection.INBOUND,
                message_type=CommunicationMessageType.REPLY,
                content=content,
                recipient_phone=from_phone,
                whatsapp_message_id=whatsapp_message_id,
                status=CommunicationStatus.READ,  # Mensajes entrantes ya están leídos
                interest_status=InterestStatus(interest_status) if interest_status else None,
                response_metadata=metadata
            )
        else:
            # Buscar la aplicación más reciente del candidato
            from app.models.core_ats import HHApplication
            
            app_result = await self.db.execute(
                select(HHApplication)
                .where(HHApplication.candidate_id == candidate.candidate_id)
                .order_by(desc(HHApplication.created_at))
                .limit(1)
            )
            application = app_result.scalar_one_or_none()
            
            comm = Communication(
                application_id=application.application_id if application else None,
                candidate_id=candidate.candidate_id,
                channel=CommunicationChannel.WHATSAPP,
                direction=CommunicationDirection.INBOUND,
                message_type=CommunicationMessageType.REPLY,
                content=content,
                recipient_phone=from_phone,
                whatsapp_message_id=whatsapp_message_id,
                status=CommunicationStatus.READ,
                interest_status=InterestStatus(interest_status) if interest_status else None,
                response_metadata=metadata
            )
        
        self.db.add(comm)
        await self.db.commit()
        await self.db.refresh(comm)
        
        return comm
    
    async def update_reply_status(
        self,
        from_phone: str,
        reply_whatsapp_id: str,
        reply_content: str,
        interest_status: str
    ):
        """Actualiza el estado de respuesta de un mensaje enviado.
        
        Args:
            from_phone: Número de teléfono
            reply_whatsapp_id: ID del mensaje de respuesta
            reply_content: Contenido de la respuesta
            interest_status: Estado de interés
        """
        # Buscar el mensaje outbound más reciente a este número
        result = await self.db.execute(
            select(Communication)
            .where(
                and_(
                    Communication.recipient_phone == from_phone,
                    Communication.direction == CommunicationDirection.OUTBOUND,
                    Communication.status.in_([
                        CommunicationStatus.SENT,
                        CommunicationStatus.DELIVERED,
                        CommunicationStatus.READ
                    ])
                )
            )
            .order_by(desc(Communication.sent_at))
            .limit(1)
        )
        parent_comm = result.scalar_one_or_none()
        
        if parent_comm:
            parent_comm.status = CommunicationStatus.REPLIED
            parent_comm.reply_whatsapp_id = reply_whatsapp_id
            parent_comm.reply_content = reply_content
            parent_comm.reply_received_at = datetime.utcnow()
            parent_comm.interest_status = InterestStatus(interest_status) if interest_status else None
            await self.db.commit()
            
            logger.info(f"Mensaje {parent_comm.communication_id} marcado como respondido")
    
    async def update_message_status(
        self,
        whatsapp_message_id: str,
        status: str,
        timestamp: Optional[str] = None
    ):
        """Actualiza el estado de un mensaje basado en webhook de Meta.
        
        Args:
            whatsapp_message_id: ID del mensaje en WhatsApp
            status: Nuevo estado (sent, delivered, read)
            timestamp: Timestamp del evento
        """
        result = await self.db.execute(
            select(Communication).where(
                Communication.whatsapp_message_id == whatsapp_message_id
            )
        )
        comm = result.scalar_one_or_none()
        
        if not comm:
            logger.warning(f"No se encontró comunicación para message_id: {whatsapp_message_id}")
            return
        
        # Actualizar estado
        if status == "sent":
            comm.status = CommunicationStatus.SENT
            if timestamp:
                comm.sent_at = datetime.fromtimestamp(int(timestamp))
        elif status == "delivered":
            comm.status = CommunicationStatus.DELIVERED
            if timestamp:
                comm.delivered_at = datetime.fromtimestamp(int(timestamp))
        elif status == "read":
            comm.status = CommunicationStatus.READ
            if timestamp:
                comm.read_at = datetime.fromtimestamp(int(timestamp))
        elif status == "failed":
            comm.status = CommunicationStatus.FAILED
        
        await self.db.commit()
        logger.info(f"Estado actualizado: {whatsapp_message_id} -> {status}")
    
    async def get_communications(
        self,
        application_id: Optional[UUID] = None,
        candidate_id: Optional[UUID] = None,
        status: Optional[CommunicationStatus] = None,
        channel: Optional[CommunicationChannel] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Communication]:
        """Obtiene comunicaciones filtradas.
        
        Args:
            application_id: Filtrar por aplicación
            candidate_id: Filtrar por candidato
            status: Filtrar por estado
            channel: Filtrar por canal
            limit: Límite de resultados
            offset: Offset para paginación
            
        Returns:
            Lista de comunicaciones
        """
        query = select(Communication).order_by(desc(Communication.created_at))
        
        if application_id:
            query = query.where(Communication.application_id == application_id)
        
        if candidate_id:
            query = query.where(Communication.candidate_id == candidate_id)
        
        if status:
            query = query.where(Communication.status == status)
        
        if channel:
            query = query.where(Communication.channel == channel)
        
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_communication_by_id(
        self,
        communication_id: UUID
    ) -> Optional[Communication]:
        """Obtiene una comunicación por ID.
        
        Args:
            communication_id: ID de la comunicación
            
        Returns:
            Comunicación o None
        """
        result = await self.db.execute(
            select(Communication).where(Communication.communication_id == communication_id)
        )
        return result.scalar_one_or_none()
    
    async def get_pending_messages(
        self,
        limit: int = 100
    ) -> List[Communication]:
        """Obtiene mensajes pendientes de envío.
        
        Args:
            limit: Límite de resultados
            
        Returns:
            Lista de mensajes pendientes
        """
        result = await self.db.execute(
            select(Communication)
            .where(Communication.status == CommunicationStatus.PENDING)
            .order_by(Communication.created_at)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_candidate_communication_summary(
        self,
        candidate_id: UUID
    ) -> Dict[str, Any]:
        """Obtiene un resumen de comunicaciones con un candidato.
        
        Args:
            candidate_id: ID del candidato
            
        Returns:
            Resumen con estadísticas
        """
        from sqlalchemy import func
        
        # Contar por estado
        result = await self.db.execute(
            select(
                Communication.status,
                func.count(Communication.communication_id).label('count')
            )
            .where(Communication.candidate_id == candidate_id)
            .group_by(Communication.status)
        )
        status_counts = {row.status.value: row.count for row in result.all()}
        
        # Obtener última comunicación
        result = await self.db.execute(
            select(Communication)
            .where(Communication.candidate_id == candidate_id)
            .order_by(desc(Communication.created_at))
            .limit(1)
        )
        last_comm = result.scalar_one_or_none()
        
        # Verificar si respondió positivamente
        result = await self.db.execute(
            select(Communication)
            .where(
                and_(
                    Communication.candidate_id == candidate_id,
                    Communication.interest_status == InterestStatus.INTERESTED
                )
            )
            .order_by(desc(Communication.created_at))
            .limit(1)
        )
        interested_comm = result.scalar_one_or_none()
        
        return {
            "total_messages": sum(status_counts.values()),
            "status_breakdown": status_counts,
            "last_contact": last_comm.created_at.isoformat() if last_comm else None,
            "last_message_status": last_comm.status.value if last_comm else None,
            "has_responded": interested_comm is not None,
            "response_date": interested_comm.reply_received_at.isoformat() if interested_comm and interested_comm.reply_received_at else None
        }
