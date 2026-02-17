"""Webhook handler para WhatsApp Business API."""
import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.whatsapp_service import WhatsAppService, get_whatsapp_service
from app.services.communication_service import CommunicationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook/whatsapp", tags=["WhatsApp Webhook"])


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge")
):
    """Verifica el webhook con Meta.
    
    Meta envía una solicitud GET para verificar que el endpoint es válido.
    Debemos retornar el hub_challenge si el verify_token coincide.
    
    Query params:
        hub.mode: Debe ser "subscribe"
        hub.verify_token: Token de verificación
        hub.challenge: Challenge a retornar
        
    Returns:
        El hub_challenge si la verificación es exitosa
    """
    logger.info(f"Solicitud de verificación de webhook: mode={hub_mode}")
    
    whatsapp_service = get_whatsapp_service()
    challenge = whatsapp_service.verify_webhook(
        mode=hub_mode,
        token=hub_verify_token,
        challenge=hub_challenge
    )
    
    if challenge is None:
        logger.warning("Verificación de webhook fallida")
        raise HTTPException(status_code=403, detail="Verification failed")
    
    # Retornar el challenge como texto plano
    return PlainTextResponse(content=challenge)


@router.post("")
async def receive_message(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Recibe mensajes y actualizaciones de estado de WhatsApp.
    
    Meta envía webhooks POST cuando:
    - Un candidato responde a un mensaje
    - El estado de un mensaje cambia (sent -> delivered -> read)
    - Otros eventos de la API
    
    Args:
        request: Request de FastAPI
        db: Sesión de base de datos
        
    Returns:
        200 OK para confirmar recepción
    """
    # Leer el cuerpo de la solicitud
    body = await request.body()
    
    # Verificar firma del webhook (opcional pero recomendado)
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    whatsapp_service = get_whatsapp_service()
    
    # Verificar firma si está configurado App Secret
    if settings.WHATSAPP_APP_SECRET:
        if not whatsapp_service.verify_webhook_signature(body, signature):
            logger.warning("Firma de webhook inválida")
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parsear JSON
    try:
        webhook_data = await request.json()
    except Exception as e:
        logger.error(f"Error parseando JSON del webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Procesar el mensaje
    result = await whatsapp_service.process_incoming_message(webhook_data)
    
    if not result.get("success"):
        logger.warning(f"No se pudo procesar el mensaje: {result.get('error')}")
        # Aún así retornar 200 para que Meta no reintente
        return JSONResponse(content={"status": "ignored"})
    
    # Procesar según el tipo
    if result.get("type") == "message":
        await _handle_incoming_message(result, db)
    elif result.get("type") == "status_update":
        await _handle_status_update(result, db)
    
    # Siempre retornar 200 OK a Meta
    return JSONResponse(content={"status": "received"})


async def _handle_incoming_message(
    message_data: dict,
    db: AsyncSession
):
    """Procesa un mensaje entrante del candidato.
    
    Args:
        message_data: Datos del mensaje procesado
        db: Sesión de base de datos
    """
    from_phone = message_data.get("from")
    content = message_data.get("content", "")
    message_id = message_data.get("message_id")
    context = message_data.get("context", {})
    
    logger.info(f"Mensaje recibido de {from_phone}: {content[:50]}...")
    
    # Buscar comunicación previa
    comm_service = CommunicationService(db)
    
    try:
        # Buscar el candidato por número de teléfono
        # Nota: Esto requiere que tengamos un servicio de candidatos que busque por teléfono
        # Por ahora, intentamos encontrar la comunicación más reciente a este número
        
        # Actualizar el estado basado en la respuesta
        interest = context.get("interest", "unknown")
        response_type = context.get("response_type", "neutral")
        
        # Crear registro de respuesta
        await comm_service.record_inbound_message(
            from_phone=from_phone,
            whatsapp_message_id=message_id,
            content=content,
            interest_status=interest,
            metadata={
                "response_type": response_type,
                "should_follow_up": context.get("should_follow_up", False)
            }
        )
        
        # Si es una respuesta a un mensaje previo, actualizar ese mensaje
        await comm_service.update_reply_status(
            from_phone=from_phone,
            reply_whatsapp_id=message_id,
            reply_content=content,
            interest_status=interest
        )
        
        logger.info(f"Respuesta procesada: interés={interest}, tipo={response_type}")
        
    except Exception as e:
        logger.error(f"Error procesando mensaje entrante: {e}")
        # No lanzar excepción para no afectar la respuesta a Meta


async def _handle_status_update(
    status_data: dict,
    db: AsyncSession
):
    """Procesa una actualización de estado de mensaje.
    
    Args:
        status_data: Datos del estado
        db: Sesión de base de datos
    """
    message_id = status_data.get("message_id")
    status = status_data.get("status")
    timestamp = status_data.get("timestamp")
    
    logger.info(f"Actualización de estado: message_id={message_id}, status={status}")
    
    try:
        comm_service = CommunicationService(db)
        await comm_service.update_message_status(
            whatsapp_message_id=message_id,
            status=status,
            timestamp=timestamp
        )
    except Exception as e:
        logger.error(f"Error actualizando estado: {e}")


@router.get("/health")
async def webhook_health():
    """Endpoint para verificar que el webhook está funcionando."""
    return {
        "status": "ok",
        "webhook_path": "/webhook/whatsapp",
        "verify_token_configured": bool(settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN),
        "app_secret_configured": bool(settings.WHATSAPP_APP_SECRET)
    }
