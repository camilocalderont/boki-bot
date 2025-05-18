import httpx, logging
from app.core.config import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()

class WhatsAppAPIError(Exception):
    """Error al llamar a la Cloud API."""

class WhatsAppClient:
    """
    Encapsula las llamadas a la Cloud API.
    Responsabilidad única: enviar mensajes salientes.
    """
    def __init__(self):
        self.url = f"{settings.BASE_URL}/{settings.PHONE_ID}/messages"
        self.headers = {
            "Authorization": f"Bearer {settings.META_TOKEN}",
            "Content-Type": "application/json"
        }

    async def send_text(self, to: str, text: str, reply_to: str | None = None):
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        if reply_to:
            payload["context"] = {"message_id": reply_to}

        async with httpx.AsyncClient(timeout=10) as client:

            try:
                r = await client.post(self.url, headers=self.headers, json=payload)
                r.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("WA %s – %s", exc.response.status_code, exc.response.text)
                # Propaga un error de dominio, no el de httpx
                raise WhatsAppAPIError(exc.response.text) from exc
        return r.json()
