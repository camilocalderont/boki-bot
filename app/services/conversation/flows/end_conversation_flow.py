from app.services.conversation.flows.base_flow import BaseFlow
from typing import Tuple

class EndConversationFlow(BaseFlow):
    """Implementa el flujo de fin de conversación."""

    async def process_message(self, state: dict, message: str, contact_id: str) -> Tuple[dict, str, bool]:
        """Procesa un mensaje en el flujo de finalización."""
        # Flujo simple de despedida
        response = "¡Gracias por contactarnos! Si necesitas más ayuda, no dudes en escribirnos nuevamente. ¡Que tengas un excelente día! 👋"
        
        # El flujo se completa inmediatamente
        return {}, response, True