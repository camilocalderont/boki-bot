from app.services.conversation.flows.base_flow import BaseFlow
from typing import Tuple

class FAQFlow(BaseFlow):
    """Implementa el flujo de preguntas frecuentes."""

    async def process_message(self, state: dict, message: str, contact_id: str) -> Tuple[dict, str, bool]:
        """Procesa un mensaje en el flujo de FAQ."""
        # Por ahora, un flujo básico que responde preguntas simples
        response = "Esta es una respuesta FAQ básica. El sistema está en desarrollo."
        
        # El flujo FAQ se completa después de una respuesta
        return {}, response, True