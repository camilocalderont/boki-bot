from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from app.core.config import get_settings
from app.models.message import WebhookPayload
from app.services.whatsapp import WhatsAppClient, WhatsAppAPIError
from app.services.conversation.conversation_manager import ConversationManager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook")
settings = get_settings()
conversation_manager = ConversationManager()

# --- GET: verificación ------------------------------------------------------
@router.get("")
async def verify_webhook(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.VERIFY_TOKEN:
        # devolver el reto como texto plano
        return PlainTextResponse(content=hub_challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Verification failed")

# --- POST: mensajes ---------------------------------------------------------
@router.post("")
async def receive_update(payload: WebhookPayload):
    try:
        # Intentar extraer el mensaje
        try:
            change = payload.entry[0].changes[0]
            message = change.value.messages[0]
        except (IndexError, AttributeError):
            # Puede ser un webhook de estado o sin mensajes
            return {"status": "ignored"}

        # Extraer información del mensaje
        from_number = message.from_

        # Extraer el contenido según el tipo de mensaje
        message_text = ""
        if message.type == "text" and message.text:
            message_text = message.text.get("body", "")
        elif message.type in ["image", "audio", "document"]:
            # Para otros tipos de mensajes, usar un texto predeterminado
            message_text = f"[Se recibió un {message.type}]"

        # Procesar el mensaje a través del gestor de conversaciones
        response_text = await conversation_manager.process_message(from_number, message_text)

        # Enviar respuesta
        await WhatsAppClient().send_text(from_number, response_text)

        return {"status": "processed"}

    except WhatsAppAPIError as exc:
        logger.warning("Fallo al enviar mensaje WA: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="WhatsApp API rejected the message"
        ) from exc
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )
