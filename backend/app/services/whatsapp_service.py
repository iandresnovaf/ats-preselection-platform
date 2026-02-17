"""Servicio de WhatsApp Business API para comunicaciones con candidatos."""
import logging
import hmac
import hashlib
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppMessageStatus(str, Enum):
    """Estados de un mensaje de WhatsApp."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    PENDING = "pending"


class WhatsAppMessageType(str, Enum):
    """Tipos de mensaje."""
    INITIAL = "initial"
    FOLLOW_UP = "follow_up"
    REMINDER = "reminder"
    REPLY = "reply"


class WhatsAppService:
    """Servicio para interactuar con WhatsApp Business API de Meta."""
    
    BASE_URL = "https://graph.facebook.com"
    
    # Templates predefinidos (deben ser aprobados por Meta)
    TEMPLATES = {
        "contacto_inicial": {
            "name": "contacto_inicial",
            "language": "es",
            "category": "UTILITY",
            "components": [
                {
                    "type": "BODY",
                    "text": "Hola {{1}}, soy {{2}} de Top Management. Tenemos una oportunidad laboral que podría interesarte: {{3}}. ¿Te gustaría conocer más detalles?"
                }
            ]
        },
        "seguimiento": {
            "name": "seguimiento",
            "language": "es",
            "category": "UTILITY",
            "components": [
                {
                    "type": "BODY",
                    "text": "Hola {{1}}, te escribo para hacer seguimiento a la oportunidad que te compartí. ¿Tuviste chance de revisarla? Quedo atento a tu respuesta."
                }
            ]
        },
        "recordatorio_entrevista": {
            "name": "recordatorio_entrevista",
            "language": "es",
            "category": "UTILITY",
            "components": [
                {
                    "type": "BODY",
                    "text": "Hola {{1}}, te recordamos que tienes una entrevista programada para {{2}} a las {{3}}. {{4}}"
                }
            ]
        },
        "rechazo_amable": {
            "name": "rechazo_amable",
            "language": "es",
            "category": "UTILITY",
            "components": [
                {
                    "type": "BODY",
                    "text": "Hola {{1}}, agradecemos tu interés en la posición de {{2}}. Después de revisar tu perfil, hemos decidido avanzar con otros candidatos. Te deseamos éxito en tu búsqueda."
                }
            ]
        },
        "oferta_laboral": {
            "name": "oferta_laboral",
            "language": "es",
            "category": "UTILITY",
            "components": [
                {
                    "type": "BODY",
                    "text": "¡Felicidades {{1}}! Has sido seleccionado para la posición de {{2}}. Nos pondremos en contacto contigo para discutir los detalles de la oferta."
                }
            ]
        }
    }
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        business_account_id: Optional[str] = None,
        api_version: Optional[str] = None,
        mock_mode: Optional[bool] = None
    ):
        """Inicializa el servicio de WhatsApp.
        
        Args:
            access_token: Token de acceso de Meta (opcional, usa settings por defecto)
            phone_number_id: ID del número de teléfono (opcional)
            business_account_id: ID de la cuenta de negocio (opcional)
            api_version: Versión de la API (opcional)
            mock_mode: Modo mock para testing (opcional)
        """
        self.access_token = access_token or settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID
        self.business_account_id = business_account_id or settings.WHATSAPP_BUSINESS_ACCOUNT_ID
        self.api_version = api_version or settings.WHATSAPP_API_VERSION
        self.mock_mode = mock_mode if mock_mode is not None else settings.WHATSAPP_MOCK_MODE
        
        self.base_url = f"{self.BASE_URL}/{self.api_version}"
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """Obtiene o crea el cliente HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    def _format_phone_number(self, phone: str) -> str:
        """Formatea el número de teléfono al formato E.164.
        
        Args:
            phone: Número de teléfono (ej: "573001234567" o "+57 300 123 4567")
            
        Returns:
            Número formateado (ej: "573001234567")
        """
        # Remover espacios, guiones, paréntesis y el signo +
        cleaned = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
        
        # Asegurar que solo contenga dígitos
        cleaned = ''.join(filter(str.isdigit, cleaned))
        
        # Validar longitud (E.164: máximo 15 dígitos)
        if len(cleaned) > 15:
            logger.warning(f"Número de teléfono demasiado largo: {len(cleaned)} dígitos")
            cleaned = cleaned[:15]
        
        return cleaned
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Obtiene los headers de autenticación."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        language_code: str = "es",
        components: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        """Envía un mensaje usando una plantilla aprobada por Meta.
        
        Args:
            to_phone: Número de teléfono del destinatario (E.164)
            template_name: Nombre de la plantilla (ej: "contacto_inicial")
            language_code: Código de idioma (default: "es")
            components: Variables para la plantilla (lista de componentes)
            
        Returns:
            Respuesta de la API con message_id
            
        Raises:
            ValueError: Si faltan credenciales o la plantilla no existe
            httpx.HTTPStatusError: Si la API retorna error
        """
        # Modo mock: simular envío exitoso
        if self.mock_mode:
            logger.info(f"[MOCK] Enviando template '{template_name}' a {to_phone}")
            return {
                "success": True,
                "mock": True,
                "message_id": f"mock_{datetime.utcnow().timestamp()}",
                "recipient": to_phone,
                "template": template_name
            }
        
        # Validar configuración
        if not self.access_token or not self.phone_number_id:
            raise ValueError("WhatsApp no configurado. Falta access_token o phone_number_id")
        
        # Formatear número
        formatted_phone = self._format_phone_number(to_phone)
        
        # Construir payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": formatted_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        # Agregar componentes si existen
        if components:
            payload["template"]["components"] = components
        
        # Enviar mensaje
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        try:
            client = self._get_client()
            response = await client.post(
                url,
                headers=self._get_auth_headers(),
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Mensaje enviado a {to_phone}: {data.get('messages', [{}])[0].get('id')}")
            
            return {
                "success": True,
                "message_id": data.get("messages", [{}])[0].get("id"),
                "recipient": formatted_phone,
                "template": template_name,
                "status": "sent"
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Error enviando mensaje: {e.response.text}")
            error_data = e.response.json() if e.response.content else {}
            return {
                "success": False,
                "error": error_data.get("error", {}).get("message", str(e)),
                "error_code": error_data.get("error", {}).get("code"),
                "recipient": formatted_phone
            }
        except Exception as e:
            logger.error(f"Error inesperado enviando mensaje: {e}")
            return {
                "success": False,
                "error": str(e),
                "recipient": formatted_phone
            }
    
    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def send_text_message(
        self,
        to_phone: str,
        message: str
    ) -> Dict[str, Any]:
        """Envía un mensaje de texto (solo dentro de la ventana de 24h).
        
        Args:
            to_phone: Número de teléfono del destinatario
            message: Texto del mensaje
            
        Returns:
            Respuesta de la API
            
        Note:
            Solo funciona si el candidato ha respondido en las últimas 24 horas
            o si se ha iniciado una conversación con template message.
        """
        # Modo mock
        if self.mock_mode:
            logger.info(f"[MOCK] Enviando mensaje de texto a {to_phone}: {message[:50]}...")
            return {
                "success": True,
                "mock": True,
                "message_id": f"mock_{datetime.utcnow().timestamp()}",
                "recipient": to_phone
            }
        
        if not self.access_token or not self.phone_number_id:
            raise ValueError("WhatsApp no configurado")
        
        formatted_phone = self._format_phone_number(to_phone)
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": formatted_phone,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        try:
            client = self._get_client()
            response = await client.post(
                url,
                headers=self._get_auth_headers(),
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                "success": True,
                "message_id": data.get("messages", [{}])[0].get("id"),
                "recipient": formatted_phone,
                "status": "sent"
            }
            
        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            error_message = error_data.get("error", {}).get("message", str(e))
            
            # Detectar error de ventana de 24h
            if "24 hours" in error_message.lower() or "outside allowed window" in error_message.lower():
                return {
                    "success": False,
                    "error": "Ventana de 24h expirada. Usa un template message.",
                    "error_code": "window_expired",
                    "recipient": formatted_phone
                }
            
            logger.error(f"Error enviando mensaje de texto: {error_message}")
            return {
                "success": False,
                "error": error_message,
                "error_code": error_data.get("error", {}).get("code"),
                "recipient": formatted_phone
            }
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return {
                "success": False,
                "error": str(e),
                "recipient": formatted_phone
            }
    
    async def get_message_status(
        self,
        message_id: str
    ) -> Dict[str, Any]:
        """Obtiene el estado de un mensaje enviado.
        
        Args:
            message_id: ID del mensaje devuelto por send_*_message
            
        Returns:
            Estado del mensaje (sent, delivered, read, failed)
        """
        if self.mock_mode:
            return {
                "success": True,
                "mock": True,
                "message_id": message_id,
                "status": "read"
            }
        
        if not self.access_token:
            raise ValueError("WhatsApp no configurado")
        
        url = f"{self.base_url}/{message_id}"
        
        try:
            client = self._get_client()
            response = await client.get(
                url,
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                "success": True,
                "message_id": message_id,
                "status": data.get("status", "unknown"),
                "timestamp": data.get("timestamp")
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Error obteniendo estado: {e.response.text}")
            return {
                "success": False,
                "error": str(e),
                "message_id": message_id
            }
    
    def verify_webhook(
        self,
        mode: str,
        token: str,
        challenge: str
    ) -> Optional[str]:
        """Verifica la solicitud de webhook de Meta.
        
        Args:
            mode: Debe ser "subscribe"
            token: Token de verificación
            challenge: Challenge a retornar si la verificación es exitosa
            
        Returns:
            El challenge si la verificación es exitosa, None si falla
        """
        verify_token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        
        if not verify_token:
            logger.warning("WHATSAPP_WEBHOOK_VERIFY_TOKEN no configurado")
            return None
        
        if mode == "subscribe" and token == verify_token:
            logger.info("Webhook verificado exitosamente")
            return challenge
        
        logger.warning(f"Verificación de webhook fallida: mode={mode}, token_match={token == verify_token}")
        return None
    
    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str
    ) -> bool:
        """Verifica la firma del webhook usando App Secret.
        
        Args:
            body: Cuerpo de la solicitud en bytes
            signature: Firma del header X-Hub-Signature-256
            
        Returns:
            True si la firma es válida
        """
        app_secret = settings.WHATSAPP_APP_SECRET
        
        if not app_secret:
            logger.warning("WHATSAPP_APP_SECRET no configurado, omitiendo verificación de firma")
            return True
        
        if not signature:
            logger.warning("No se recibió firma en el webhook")
            return False
        
        # Calcular firma esperada
        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Comparar de forma segura (timing-safe)
        expected = f"sha256={expected_signature}"
        return hmac.compare_digest(expected, signature)
    
    async def process_incoming_message(
        self,
        webhook_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Procesa un mensaje entrante del webhook.
        
        Args:
            webhook_data: Datos del webhook de Meta
            
        Returns:
            Información del mensaje procesado
        """
        try:
            # Extraer información del mensaje
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            
            # Verificar que sea un mensaje de WhatsApp Business API
            if value.get("messaging_product") != "whatsapp":
                return {"success": False, "error": "No es un mensaje de WhatsApp"}
            
            # Procesar mensajes
            messages = value.get("messages", [])
            if not messages:
                # Podría ser un evento de estado
                statuses = value.get("statuses", [])
                if statuses:
                    return self._process_status_update(statuses[0])
                return {"success": False, "error": "No hay mensajes ni estados"}
            
            message = messages[0]
            
            result = {
                "success": True,
                "type": "message",
                "message_id": message.get("id"),
                "from": message.get("from"),
                "timestamp": message.get("timestamp"),
                "message_type": message.get("type"),
            }
            
            # Extraer contenido según tipo
            msg_type = message.get("type")
            if msg_type == "text":
                result["content"] = message.get("text", {}).get("body", "")
                result["context"] = self._analyze_response(result["content"])
            elif msg_type == "button":
                result["content"] = message.get("button", {}).get("text", "")
                result["payload"] = message.get("button", {}).get("payload", "")
                result["context"] = self._analyze_response(result["content"])
            elif msg_type == "interactive":
                interactive = message.get("interactive", {})
                reply_type = interactive.get("type")
                if reply_type == "button_reply":
                    result["content"] = interactive.get("button_reply", {}).get("title", "")
                    result["payload"] = interactive.get("button_reply", {}).get("id", "")
                elif reply_type == "list_reply":
                    result["content"] = interactive.get("list_reply", {}).get("title", "")
                    result["payload"] = interactive.get("list_reply", {}).get("id", "")
                result["context"] = self._analyze_response(result["content"])
            else:
                result["content"] = f"[Mensaje tipo: {msg_type}]"
                result["context"] = {"interest": "unknown", "response_type": "other"}
            
            # Extraer información del contacto
            contacts = value.get("contacts", [])
            if contacts:
                contact = contacts[0]
                result["contact"] = {
                    "wa_id": contact.get("wa_id"),
                    "name": contact.get("profile", {}).get("name", "")
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error procesando mensaje entrante: {e}")
            return {
                "success": False,
                "error": str(e),
                "raw_data": webhook_data
            }
    
    def _process_status_update(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa una actualización de estado de mensaje.
        
        Args:
            status: Datos del estado
            
        Returns:
            Información del estado procesado
        """
        return {
            "success": True,
            "type": "status_update",
            "message_id": status.get("id"),
            "status": status.get("status"),
            "timestamp": status.get("timestamp"),
            "recipient_id": status.get("recipient_id"),
            "conversation": status.get("conversation", {})
        }
    
    def _analyze_response(self, content: str) -> Dict[str, str]:
        """Analiza la respuesta del candidato para determinar interés.
        
        Args:
            content: Texto de la respuesta
            
        Returns:
            Diccionario con análisis de la respuesta
        """
        content_lower = content.lower().strip()
        
        # Palabras clave de interés positivo
        positive_keywords = [
            "si", "sí", "interesa", "interesado", "interesada",
            "me gusta", "cuéntame", "cuentame", "más info", "mas info",
            "adelante", "por supuesto", "claro", "ok", "perfecto",
            "envía", "envia", "mándame", "mandame", "quiero saber",
            "positivo", "afirmativo", "me interesa", "sí me interesa"
        ]
        
        # Palabras clave de rechazo
        negative_keywords = [
            "no", "no gracias", "no me interesa", "no estoy interesado",
            "no estoy buscando", "ya tengo trabajo", "no gracias",
            "paso", "rechazo", "no por ahora", "no en este momento",
            "no gracias", "paso por ahora", "estoy bien así"
        ]
        
        # Palabras clave de preguntas
        question_keywords = [
            "?", "cuanto", "cuánto", "donde", "dónde", "salario",
            "remuneración", "que empresa", "qué empresa", "horario",
            "beneficios", "ubicación", "remoto", "presencial", "hibrido"
        ]
        
        # Analizar
        is_positive = any(kw in content_lower for kw in positive_keywords)
        is_negative = any(kw in content_lower for kw in negative_keywords)
        is_question = any(kw in content_lower for kw in question_keywords) or "?" in content
        
        if is_negative:
            return {
                "interest": "not_interested",
                "response_type": "rejection",
                "should_follow_up": False
            }
        elif is_positive:
            return {
                "interest": "interested",
                "response_type": "acceptance",
                "should_follow_up": True
            }
        elif is_question:
            return {
                "interest": "interested",
                "response_type": "question",
                "should_follow_up": True
            }
        else:
            return {
                "interest": "unknown",
                "response_type": "neutral",
                "should_follow_up": True
            }
    
    async def get_templates(self) -> List[Dict[str, Any]]:
        """Obtiene las plantillas aprobadas de la cuenta.
        
        Returns:
            Lista de plantillas disponibles
        """
        if self.mock_mode:
            return [
                {
                    "name": name,
                    "status": "APPROVED",
                    "language": info["language"],
                    "category": info["category"]
                }
                for name, info in self.TEMPLATES.items()
            ]
        
        if not self.access_token or not self.business_account_id:
            raise ValueError("WhatsApp no configurado")
        
        url = f"{self.base_url}/{self.business_account_id}/message_templates"
        
        try:
            client = self._get_client()
            response = await client.get(
                url,
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Error obteniendo plantillas: {e.response.text}")
            return []
    
    async def test_connection(self) -> Dict[str, Any]:
        """Prueba la conexión con la API de WhatsApp.
        
        Returns:
            Resultado de la prueba
        """
        if self.mock_mode:
            return {
                "success": True,
                "mock": True,
                "message": "Modo mock activo - conexión simulada"
            }
        
        if not self.access_token or not self.phone_number_id:
            return {
                "success": False,
                "error": "WhatsApp no configurado. Falta access_token o phone_number_id"
            }
        
        try:
            # Intentar obtener información del número de teléfono
            url = f"{self.base_url}/{self.phone_number_id}"
            
            client = self._get_client()
            response = await client.get(
                url,
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                "success": True,
                "phone_number": data.get("display_phone_number"),
                "quality_rating": data.get("quality_rating"),
                "verified": True
            }
            
        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            return {
                "success": False,
                "error": error_data.get("error", {}).get("message", str(e)),
                "error_code": error_data.get("error", {}).get("code")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Singleton
def get_whatsapp_service(
    access_token: Optional[str] = None,
    phone_number_id: Optional[str] = None,
    mock_mode: Optional[bool] = None
) -> WhatsAppService:
    """Obtiene una instancia del servicio de WhatsApp.
    
    Args:
        access_token: Token de acceso opcional
        phone_number_id: ID del número opcional
        mock_mode: Modo mock opcional
        
    Returns:
        Instancia de WhatsAppService
    """
    return WhatsAppService(
        access_token=access_token,
        phone_number_id=phone_number_id,
        mock_mode=mock_mode
    )
