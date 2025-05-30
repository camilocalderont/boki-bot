import logging
from typing import Tuple, Dict, Union
from app.services.conversation.flows.base_flow import BaseFlow
from app.services.external import BokiApi
from .check_appointment_steps import CheckAppointmentSteps

logger = logging.getLogger(__name__)

class CheckAppointmentFlow(BaseFlow):
    """
    Responsabilidad única: Orquestar el flujo de consulta de citas.
    Coordina los pasos especializados sin lógica de negocio compleja.
    """

    def __init__(self):
        super().__init__()
        self.boki_api = BokiApi()
        self.steps = CheckAppointmentSteps(self.boki_api)

    async def process_message(self, state: Dict, message: str, contact_id: str) -> Tuple[Dict, Union[str, Dict], bool]:
        """
        Procesa un mensaje en el flujo de consulta de citas.
        Responsabilidad: Solo orquestar, delegar lógica a componentes especializados.
        """
        current_step = state.get("step", "initial")
        data = state.get("data", {})

        self.log_step(current_step, contact_id, message)

        try:
            # Para el paso inicial o cuando necesitamos el contact_id, mostrar las citas directamente
            if current_step in ["initial", "", "need_contact_id"]:
                return await self.steps.show_appointments_for_contact(contact_id)
            
            # Mapeo simple de pasos a métodos
            step_handlers = {
                "waiting_action": lambda: self.steps.process_action_selection(message, data),
            }

            # Ejecutar handler apropiado
            handler = step_handlers.get(current_step)
            if handler:
                return await handler()
            else:
                # Fallback seguro - mostrar citas
                return await self.steps.show_appointments_for_contact(contact_id)

        except Exception as e:
            self.logger.error(f"Error procesando mensaje: {e}")
            return await self.steps.show_appointments_for_contact(contact_id)  # Fallback seguro 