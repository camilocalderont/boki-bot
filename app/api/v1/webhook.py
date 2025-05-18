from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from app.core.config import get_settings
from app.models.message import WebhookPayload
from app.services.whatsapp import WhatsAppClient, WhatsAppAPIError
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook")
settings = get_settings()

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
from fastapi import HTTPException, status

@router.post("")
async def receive_update(payload: WebhookPayload):
    try:
        change = payload.entry[0].changes[0]
        message = change.value.messages[0]
    except IndexError:
        # Puede ser un webhook de estado o sin mensajes → simplemente ignóralo
        return {"status": "ignored"}

    from_number = message.from_

    try:
        await WhatsAppClient().send_text(
            from_number,
            f"👋 Hola, mundo. Recibí: {message.text['body']}"
        )
    except WhatsAppAPIError as exc:
        # Aquí decides qué hacer: log, métricas, respuesta
        logger.warning("Fallo al enviar mensaje WA: %s", exc)
        # Responder 502/500 a tu consumidor (no a Meta)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="WhatsApp API rejected the message"
        ) from exc

    return {"status": "sent"}
