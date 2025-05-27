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

    async def send_interactive(self, to: str, interactive_data: dict, reply_to: str | None = None):
        """
        Envía mensajes interactivos (botones o listas) a WhatsApp.
        
        Args:
            to: Número de teléfono destino
            interactive_data: Objeto con estructura de botones/lista
            reply_to: ID del mensaje al que responder (opcional)
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            **interactive_data  # Incluir tipo "interactive" y toda la estructura
        }
        
        if reply_to:
            payload["context"] = {"message_id": reply_to}

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                r = await client.post(self.url, headers=self.headers, json=payload)
                r.raise_for_status()
                logger.debug(f"[WA] Mensaje interactivo enviado: {interactive_data.get('interactive', {}).get('type', 'unknown')}")
            except httpx.HTTPStatusError as exc:
                logger.error("WA Interactive %s – %s", exc.response.status_code, exc.response.text)
                # Propaga un error de dominio, no el de httpx
                raise WhatsAppAPIError(exc.response.text) from exc
        return r.json()

    async def send_message(self, to: str, content, reply_to: str | None = None):
        """
        Método unificado que detecta automáticamente el tipo de mensaje.
        
        Args:
            to: Número de teléfono destino
            content: Puede ser string (texto) o dict (interactivo)
            reply_to: ID del mensaje al que responder (opcional)
        """
        if isinstance(content, dict) and content.get("type") == "interactive":
            # Es un mensaje interactivo
            return await self.send_interactive(to, content, reply_to)
        else:
            # Es texto simple
            return await self.send_text(to, str(content), reply_to)