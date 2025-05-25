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

# Crear una instancia global del conversation manager
conversation_manager = ConversationManager()

# --- GET: verificación ------------------------------------------------------
@router.get("")
async def verify_webhook(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.VERIFY_TOKEN:
        logger.info("[WEBHOOK] Verificación exitosa")
        return PlainTextResponse(content=hub_challenge, status_code=200)

    logger.warning(f"[WEBHOOK] Verificación fallida - mode: {hub_mode}, token: {hub_verify_token}")
    raise HTTPException(status_code=403, detail="Verification failed")

# --- POST: mensajes ---------------------------------------------------------
@router.post("")
async def receive_update(payload: WebhookPayload):
    try:
        # Intentar extraer el mensaje
        try:
            change = payload.entry[0].changes[0]

            # Verificar si es un webhook de estado de mensaje
            if hasattr(change.value, 'statuses') and change.value.statuses:
                return await _handle_status_update(change.value.statuses)

            # Verificar si hay mensajes
            if not hasattr(change.value, 'messages') or not change.value.messages:
                logger.debug("[WEBHOOK] Webhook sin mensajes, ignorando")
                return {"status": "ignored", "reason": "no_messages"}

            message = change.value.messages[0]

        except (IndexError, AttributeError) as e:
            logger.debug(f"[WEBHOOK] Estructura de payload inesperada: {e}")
            return {"status": "ignored", "reason": "invalid_structure"}

        # Extraer información del mensaje
        from_number = message.from_
        message_id = message.id
        message_type = getattr(message, 'type', 'unknown')

        logger.info(f"[WEBHOOK] Mensaje recibido de {from_number} (ID: {message_id}, Tipo: {message_type})")

        # Extraer el contenido según el tipo de mensaje
        message_text = ""
        if message_type == "text" and message.text:
            message_text = message.text.get("body", "")
        elif message_type in ["image", "audio", "document", "video"]:
            # Para otros tipos de mensajes, usar un texto predeterminado
            message_text = f"[Se recibió un {message_type}]"
            logger.info(f"[WEBHOOK] Mensaje multimedia recibido: {message_type}")
        else:
            logger.warning(f"[WEBHOOK] Tipo de mensaje no soportado: {message_type}")
            return {"status": "ignored", "reason": f"unsupported_type_{message_type}"}

        # Validar que hay contenido para procesar
        if not message_text.strip():
            logger.warning(f"[WEBHOOK] Mensaje vacío recibido de {from_number}")
            return {"status": "ignored", "reason": "empty_message"}

        # Procesar el mensaje a través del gestor de conversaciones
        response_text = await conversation_manager.process_message(
            phone_number=from_number,
            message_text=message_text,
            message_id=message_id
        )

        # Enviar respuesta solo si hay una respuesta que enviar
        if response_text:
            try:
                whatsapp_client = WhatsAppClient()
                wa_response = await whatsapp_client.send_text(
                    to=from_number,
                    text=response_text,
                    reply_to=message_id  # Responder al mensaje original
                )

                # Extraer el ID del mensaje enviado para logging futuro
                sent_message_id = None
                if wa_response and wa_response.get("messages"):
                    sent_message_id = wa_response["messages"][0].get("id")
                    logger.debug(f"[WEBHOOK] Respuesta enviada con WhatsApp ID: {sent_message_id}")

                logger.info(f"[WEBHOOK] Respuesta enviada exitosamente a {from_number}")
                return {
                    "status": "processed",
                    "message_id": message_id,
                    "sent_message_id": sent_message_id
                }

            except WhatsAppAPIError as exc:
                logger.error(f"[WEBHOOK] Error de WhatsApp API enviando a {from_number}: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="WhatsApp API rejected the message"
                ) from exc
        else:
            # No hay respuesta (probablemente mensaje duplicado)
            logger.debug(f"[WEBHOOK] No hay respuesta para {from_number} - posible duplicado")
            return {"status": "ignored_duplicate", "message_id": message_id}

    except HTTPException:
        # Re-lanzar excepciones HTTP sin cambios
        raise
    except Exception as e:
        logger.error(f"[WEBHOOK] Error inesperado procesando mensaje: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

# --- Función auxiliar para manejar actualizaciones de estado ---------------
async def _handle_status_update(statuses: list):
    """
    Maneja actualizaciones de estado de mensajes desde WhatsApp.
    Esto nos permite saber si los mensajes fueron entregados, leídos, etc.
    """
    try:
        logger.debug(f"[WEBHOOK] Actualizaciones de estado recibidas: {len(statuses)} estados")

        for status_update in statuses:
            message_id = status_update.get("id")
            status_value = status_update.get("status")
            timestamp = status_update.get("timestamp")

            logger.debug(f"[WEBHOOK] Estado del mensaje {message_id}: {status_value}")

            # Aquí podrías integrar con el sistema de estados que creamos
            # Por ejemplo, llamar a la API para actualizar el estado:
            # await conversation_manager.boki_api.update_message_status_by_wa_id(
            #     message_id, {"deliveryStatus": status_value}
            # )

        return {"status": "status_received", "count": len(statuses)}

    except Exception as e:
        logger.error(f"[WEBHOOK] Error procesando actualizaciones de estado: {e}")
        return {"status": "status_error"}