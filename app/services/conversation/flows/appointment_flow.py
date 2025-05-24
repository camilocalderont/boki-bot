from app.services.conversation.flows.base_flow import BaseFlow
from typing import Tuple

class AppointmentFlow(BaseFlow):
    """Implementa el flujo de agendamiento de citas."""

    async def process_message(self, state: dict, message: str, contact_id: str) -> Tuple[dict, str, bool]:
        """Procesa un mensaje en el flujo de citas."""
        # Por ahora, un flujo básico para agendar citas
        response = "Gracias por tu interés en agendar una cita. El sistema de citas está en desarrollo."
        
        # El flujo de citas se completa después de una respuesta
        return {}, response, True