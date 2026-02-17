"""API de Comunicaciones - Envío y gestión de mensajes a candidatos."""
import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas import MessageResponse
from app.services.communication_service import CommunicationService
from app.services.whatsapp_service import WhatsAppService, get_whatsapp_service
from app.models.communication import (
    CommunicationChannel,
    CommunicationMessageType,
    CommunicationStatus
)
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/communications", tags=["Communications"])


# ============== SCHEMAS ==============

class SendMessageRequest(BaseModel):
    """Request para enviar mensaje."""
    application_id: UUID = Field(..., description="ID de la aplicación")
    candidate_id: UUID = Field(..., description="ID del candidato")
    phone: str = Field(..., description="Número de teléfono (formato internacional)", min_length=8, max_length=25)
    template_name: str = Field(..., description="Nombre del template de WhatsApp", min_length=1, max_length=100)
    template_variables: Optional[List[str]] = Field(default=[], description="Variables para el template")
    message_type: str = Field(default="initial", description="Tipo de mensaje: initial, follow_up, reminder")
    
    class Config:
        json_schema_extra = {
            "example": {
                "application_id": "550e8400-e29b-41d4-a716-446655440000",
                "candidate_id": "550e8400-e29b-41d4-a716-446655440001",
                "phone": "573001234567",
                "template_name": "contacto_inicial",
                "template_variables": ["Juan Pérez", "María González", "Gerente de Ventas"],
                "message_type": "initial"
            }
        }


class SendMessageResponse(BaseModel):
    """Response de envío de mensaje."""
    success: bool
    communication_id: Optional[UUID] = None
    whatsapp_message_id: Optional[str] = None
    status: str
    error: Optional[str] = None


class CommunicationResponse(BaseModel):
    """Response de comunicación."""
    communication_id: UUID
    application_id: Optional[UUID]
    candidate_id: Optional[UUID]
    channel: str
    direction: str
    message_type: str
    template_id: Optional[str]
    content: str
    recipient_phone: Optional[str]
    whatsapp_message_id: Optional[str]
    status: str
    sent_at: Optional[str]
    delivered_at: Optional[str]
    read_at: Optional[str]
    reply_content: Optional[str]
    reply_received_at: Optional[str]
    interest_status: Optional[str]
    error_message: Optional[str]
    retry_count: int
    created_at: str


class CommunicationListResponse(BaseModel):
    """Response de lista de comunicaciones."""
    items: List[CommunicationResponse]
    total: int


class RetryMessageResponse(BaseModel):
    """Response de reintento."""
    success: bool
    communication_id: UUID
    status: str
    retry_count: int
    error: Optional[str] = None


class CandidateCommunicationSummary(BaseModel):
    """Resumen de comunicaciones con un candidato."""
    total_messages: int
    status_breakdown: dict
    last_contact: Optional[str]
    last_message_status: Optional[str]
    has_responded: bool
    response_date: Optional[str]


class WhatsAppTemplate(BaseModel):
    """Template de WhatsApp."""
    name: str
    status: str
    language: str
    category: str


class WhatsAppStatusResponse(BaseModel):
    """Estado de la conexión con WhatsApp."""
    enabled: bool
    mock_mode: bool
    connected: bool
    phone_number: Optional[str]
    error: Optional[str]


# ============== ENDPOINTS ==============

@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Envía un mensaje de WhatsApp a un candidato.
    
    Requiere configuración de WhatsApp Business API o estar en modo mock.
    
    - **application_id**: ID de la aplicación/postulación
    - **candidate_id**: ID del candidato
    - **phone**: Número de teléfono en formato internacional (ej: 573001234567)
    - **template_name**: Nombre del template aprobado por Meta
    - **template_variables**: Lista de variables para el template
    - **message_type**: Tipo de mensaje (initial, follow_up, reminder)
    """
    try:
        comm_service = CommunicationService(db)
        
        # Mapear tipo de mensaje
        msg_type = CommunicationMessageType.INITIAL
        if request.message_type == "follow_up":
            msg_type = CommunicationMessageType.FOLLOW_UP
        elif request.message_type == "reminder":
            msg_type = CommunicationMessageType.REMINDER
        
        # Enviar mensaje
        comm = await comm_service.send_whatsapp_message(
            application_id=request.application_id,
            candidate_id=request.candidate_id,
            to_phone=request.phone,
            template_name=request.template_name,
            template_variables=request.template_variables,
            message_type=msg_type,
            created_by=current_user.id
        )
        
        return SendMessageResponse(
            success=comm.status != CommunicationStatus.FAILED,
            communication_id=comm.communication_id,
            whatsapp_message_id=comm.whatsapp_message_id,
            status=comm.status.value,
            error=comm.error_message
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error enviando mensaje: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando mensaje: {str(e)}"
        )


@router.get("", response_model=CommunicationListResponse)
async def list_communications(
    application_id: Optional[UUID] = Query(None, description="Filtrar por aplicación"),
    candidate_id: Optional[UUID] = Query(None, description="Filtrar por candidato"),
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    channel: Optional[str] = Query(None, description="Filtrar por canal"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista comunicaciones con filtros opcionales."""
    try:
        comm_service = CommunicationService(db)
        
        # Convertir strings a enums
        status_enum = None
        if status:
            try:
                status_enum = CommunicationStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Estado inválido: {status}"
                )
        
        channel_enum = None
        if channel:
            try:
                channel_enum = CommunicationChannel(channel)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Canal inválido: {channel}"
                )
        
        communications = await comm_service.get_communications(
            application_id=application_id,
            candidate_id=candidate_id,
            status=status_enum,
            channel=channel_enum,
            limit=limit,
            offset=offset
        )
        
        # Convertir a response
        items = []
        for comm in communications:
            items.append(CommunicationResponse(
                communication_id=comm.communication_id,
                application_id=comm.application_id,
                candidate_id=comm.candidate_id,
                channel=comm.channel.value,
                direction=comm.direction.value,
                message_type=comm.message_type.value,
                template_id=comm.template_id,
                content=comm.content,
                recipient_phone=comm.recipient_phone,
                whatsapp_message_id=comm.whatsapp_message_id,
                status=comm.status.value,
                sent_at=comm.sent_at.isoformat() if comm.sent_at else None,
                delivered_at=comm.delivered_at.isoformat() if comm.delivered_at else None,
                read_at=comm.read_at.isoformat() if comm.read_at else None,
                reply_content=comm.reply_content,
                reply_received_at=comm.reply_received_at.isoformat() if comm.reply_received_at else None,
                interest_status=comm.interest_status.value if comm.interest_status else None,
                error_message=comm.error_message,
                retry_count=comm.retry_count,
                created_at=comm.created_at.isoformat()
            ))
        
        return CommunicationListResponse(
            items=items,
            total=len(items)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando comunicaciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listando comunicaciones: {str(e)}"
        )


@router.post("/{communication_id}/retry", response_model=RetryMessageResponse)
async def retry_message(
    communication_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reintenta enviar un mensaje fallido."""
    try:
        comm_service = CommunicationService(db)
        comm = await comm_service.retry_failed_message(communication_id)
        
        return RetryMessageResponse(
            success=comm.status != CommunicationStatus.FAILED,
            communication_id=comm.communication_id,
            status=comm.status.value,
            retry_count=comm.retry_count,
            error=comm.error_message
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error reintentando mensaje: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reintentando mensaje: {str(e)}"
        )


@router.get("/{communication_id}", response_model=CommunicationResponse)
async def get_communication(
    communication_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene una comunicación por ID."""
    try:
        comm_service = CommunicationService(db)
        comm = await comm_service.get_communication_by_id(communication_id)
        
        if not comm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comunicación no encontrada"
            )
        
        return CommunicationResponse(
            communication_id=comm.communication_id,
            application_id=comm.application_id,
            candidate_id=comm.candidate_id,
            channel=comm.channel.value,
            direction=comm.direction.value,
            message_type=comm.message_type.value,
            template_id=comm.template_id,
            content=comm.content,
            recipient_phone=comm.recipient_phone,
            whatsapp_message_id=comm.whatsapp_message_id,
            status=comm.status.value,
            sent_at=comm.sent_at.isoformat() if comm.sent_at else None,
            delivered_at=comm.delivered_at.isoformat() if comm.delivered_at else None,
            read_at=comm.read_at.isoformat() if comm.read_at else None,
            reply_content=comm.reply_content,
            reply_received_at=comm.reply_received_at.isoformat() if comm.reply_received_at else None,
            interest_status=comm.interest_status.value if comm.interest_status else None,
            error_message=comm.error_message,
            retry_count=comm.retry_count,
            created_at=comm.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo comunicación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo comunicación: {str(e)}"
        )


@router.get("/candidate/{candidate_id}/summary", response_model=CandidateCommunicationSummary)
async def get_candidate_summary(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene un resumen de comunicaciones con un candidato."""
    try:
        comm_service = CommunicationService(db)
        summary = await comm_service.get_candidate_communication_summary(candidate_id)
        return CandidateCommunicationSummary(**summary)
        
    except Exception as e:
        logger.error(f"Error obteniendo resumen: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo resumen: {str(e)}"
        )


@router.get("/whatsapp/status", response_model=WhatsAppStatusResponse)
async def get_whatsapp_status(
    current_user: User = Depends(get_current_user)
):
    """Verifica el estado de la conexión con WhatsApp Business API."""
    from app.core.config import settings
    
    try:
        whatsapp_service = get_whatsapp_service()
        result = await whatsapp_service.test_connection()
        
        return WhatsAppStatusResponse(
            enabled=settings.WHATSAPP_ENABLED or settings.WHATSAPP_MOCK_MODE,
            mock_mode=settings.WHATSAPP_MOCK_MODE,
            connected=result.get("success", False),
            phone_number=result.get("phone_number"),
            error=result.get("error")
        )
        
    except Exception as e:
        return WhatsAppStatusResponse(
            enabled=settings.WHATSAPP_ENABLED or settings.WHATSAPP_MOCK_MODE,
            mock_mode=settings.WHATSAPP_MOCK_MODE,
            connected=False,
            error=str(e)
        )


@router.get("/whatsapp/templates", response_model=List[WhatsAppTemplate])
async def list_whatsapp_templates(
    current_user: User = Depends(get_current_user)
):
    """Lista los templates disponibles en WhatsApp Business API."""
    try:
        whatsapp_service = get_whatsapp_service()
        templates = await whatsapp_service.get_templates()
        
        return [
            WhatsAppTemplate(
                name=t.get("name", ""),
                status=t.get("status", ""),
                language=t.get("language", ""),
                category=t.get("category", "")
            )
            for t in templates
        ]
        
    except Exception as e:
        logger.error(f"Error obteniendo templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo templates: {str(e)}"
        )
