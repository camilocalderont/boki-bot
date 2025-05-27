import logging
from typing import Tuple, Dict, Union
from app.services.conversation.flows.base_flow import BaseFlow
from app.services.external import BokiApi
from .appointment_steps import AppointmentSteps

logger = logging.getLogger(__name__)

class AppointmentFlow(BaseFlow):
    """
    Responsabilidad única: Orquestar el flujo de agendamiento.
    Coordina los pasos especializados sin lógica de negocio compleja.
    """

    def __init__(self):
        super().__init__()
        self.boki_api = BokiApi()
        self.steps = AppointmentSteps(self.boki_api)

    async def process_message(self, state: Dict, message: str, contact_id: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """
        Procesa un mensaje en el flujo de agendamiento.
        Responsabilidad: Solo orquestar, delegar lógica a componentes especializados.
        """
        current_step = state.get("step", "initial")
        data = state.get("data", {})

        self.log_step(current_step, contact_id, message)

        try:
            # Mapeo simple de pasos a métodos
            step_handlers = {
                "initial": self.steps.show_categories,
                "": self.steps.show_categories,
                "waiting_category": lambda: self.steps.process_category_selection(message, data),
                "waiting_service": lambda: self.steps.process_service_selection(message, data),
                "waiting_professional": lambda: self.steps.process_professional_selection(message, data),
                "waiting_date": lambda: self.steps.process_date_selection(message, data),
                "waiting_time": lambda: self.steps.process_time_selection(message, data),
                "waiting_confirmation": lambda: self.steps.process_confirmation(message, data, contact_id)
            }

            # Ejecutar handler apropiado
            handler = step_handlers.get(current_step, self.steps.show_categories)
            return await handler()

        except Exception as e:
            self.logger.error(f"Error procesando mensaje: {e}")
            return await self.steps.show_categories()  # Fallback seguro