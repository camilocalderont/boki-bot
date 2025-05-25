from app.services.conversation.flows.base_flow import BaseFlow
from typing import Tuple

class SupportFlow(BaseFlow):
    """Implementa el flujo de soporte técnico."""

    async def process_message(self, state: dict, message: str, contact_id: str) -> Tuple[dict, str, bool]:
        """Procesa un mensaje en el flujo de soporte."""
        response = (
            "Entiendo que tienes un problema técnico. 🛠️\n\n"
            "Por favor describe detalladamente tu problema y "
            "un miembro de nuestro equipo de soporte te contactará pronto.\n\n"
            "¿Hay algo más en lo que pueda ayudarte?"
        )

        # El flujo de soporte se completa después de una respuesta
        return {}, response, True