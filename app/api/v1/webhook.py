from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from app.core.config import get_settings
from app.models.message import WebhookPayload
from app.services.whatsapp import WhatsAppClient, WhatsAppAPIError
from app.services.conversation import ConversationManager
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook")
settings = get_settings()

# Instancia global del conversation manager
conversation_manager = ConversationManager()

# ============================================================================
# ENDPOINTS PRINCIPALES
# ============================================================================

@router.get("")
async def verify_webhook(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
):
    """Verifica el webhook de WhatsApp Business API."""
    if hub_mode == "subscribe" and hub_verify_token == settings.VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge, status_code=200)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("")
async def receive_update(payload: WebhookPayload):
    """
    Endpoint principal para recibir actualizaciones de WhatsApp.
    Responsabilidad: Orquestación y manejo de errores.
    """
    try:
        # 1. Extraer mensaje del payload
        message_data = _extract_message_from_payload(payload)
        if not message_data:
            return {"status": "ignored", "reason": "no_valid_message"}

        # 3. Procesar mensaje de chat
        return await _process_chat_message(message_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

# ============================================================================
# FUNCIONES PRIVADAS - EXTRACCIÓN Y VALIDACIÓN
# ============================================================================

def _extract_message_from_payload(payload: WebhookPayload) -> Optional[Dict[str, Any]]:
    """
    Extrae y valida el mensaje del payload de WhatsApp.
    Responsabilidad: Parsing y validación de estructura.
    """
    try:
        logger.debug(f"📥 Payload recibido: {payload}")
        
        change = payload.entry[0].changes[0]

        # Verificar si es actualización de estado
        if hasattr(change.value, 'statuses') and change.value.statuses:
            return {
                "type": "status_update",
                "statuses": change.value.statuses
            }

        # Verificar si hay mensajes
        if not hasattr(change.value, 'messages') or not change.value.messages:
            return None

        message = change.value.messages[0]
        
        result = {
            "type": "chat_message",
            "message": message,
            "from_number": message.from_,
            "message_id": message.id,
            "message_type": getattr(message, 'type', 'unknown')
        }
        
        return result

    except (IndexError, AttributeError) as e:
        logger.error(f"❌ Error extrayendo mensaje del payload: {e}")
        logger.error(f"📋 Payload completo: {payload}")
        return None


def _extract_message_content(message_data: Dict[str, Any]) -> Optional[str]:
    """
    Extrae el contenido del mensaje según su tipo.
    Responsabilidad: Parsing de contenido específico por tipo.
    """
    try:
        # Verificar que tengamos la estructura correcta
        if "message" not in message_data:
            logger.warning(f"message_data no tiene 'message': {message_data}")
            return None
            
        message = message_data["message"]
        message_type = message_data.get("message_type", "unknown")
        
        # Mensaje de texto
        if message_type == "text" and hasattr(message, 'text') and message.text:
            return message.text.get("body", "")

        # Mensaje interactivo (botones/listas)
        elif message_type == "interactive" and hasattr(message, 'interactive') and message.interactive:
            return _extract_interactive_content(message.interactive)

        # Mensajes multimedia
        elif message_type in ["image", "audio", "document", "video"]:
            return f"[Se recibió un {message_type}]"

        # Tipo no soportado
        else:
            logger.warning(f"Tipo de mensaje no soportado: {message_type}")
            return None
            
    except Exception as e:
        logger.error(f"Error extrayendo contenido del mensaje: {e}")
        logger.error(f"message_data: {message_data}")
        return None


def _extract_interactive_content(interactive) -> str:
    """
    Extrae contenido de mensajes interactivos (botones/listas).
    Responsabilidad: Parsing específico de elementos interactivos.
    """
    if interactive.type == "button_reply" and interactive.button_reply:
        return interactive.button_reply.id

    elif interactive.type == "list_reply" and interactive.list_reply:
        return interactive.list_reply.id

    else:
        logger.warning(f"Tipo interactivo no soportado: {interactive.type}")
        return "interactive_unknown"

# ============================================================================
# FUNCIONES PRIVADAS - PROCESAMIENTO
# ============================================================================

async def _process_chat_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa un mensaje de chat completo.
    Responsabilidad: Orquestación del procesamiento de mensajes.
    """
    # Extraer contenido del mensaje
    message_text = _extract_message_content(message_data)
    
    if not message_text or not message_text.strip():
        return {"status": "ignored", "reason": "empty_message"}

    # Procesar mensaje a través del conversation manager
    response_text = await conversation_manager.process_message(
        phone_number=message_data["from_number"],
        message_text=message_text,
        message_id=message_data["message_id"]
    )

    # Enviar respuesta si existe
    if response_text:
        return await _send_whatsapp_response(
            to=message_data["from_number"],
            content=response_text,
            reply_to=message_data["message_id"]
        )
    else:
        return {"status": "ignored_duplicate", "message_id": message_data["message_id"]}


async def _send_whatsapp_response(to: str, content: Any, reply_to: str) -> Dict[str, Any]:
    """
    Envía respuesta a WhatsApp y maneja errores.
    Responsabilidad: Envío de respuestas y manejo de errores de API.
    """
    try:
        whatsapp_client = WhatsAppClient()
        
        # Usar el método unificado que detecta automáticamente el tipo
        wa_response = await whatsapp_client.send_message(
            to=to,
            content=content,  # Puede ser string o dict de botones
            reply_to=reply_to
        )

        # Extraer ID del mensaje enviado
        sent_message_id = None
        if wa_response and wa_response.get("messages"):
            sent_message_id = wa_response["messages"][0].get("id")

        return {
            "status": "processed",
            "message_id": reply_to,
            "sent_message_id": sent_message_id
        }

    except WhatsAppAPIError as exc:
        logger.error(f"Error enviando mensaje a WhatsApp: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="WhatsApp API rejected the message"
        ) from exc
