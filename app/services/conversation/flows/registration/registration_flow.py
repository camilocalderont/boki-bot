import logging
from typing import Tuple, Dict
from app.services.conversation.flows.base_flow import BaseFlow
from app.services.external import BokiApi
from .registration_steps import RegistrationSteps

logger = logging.getLogger(__name__)

class RegistrationFlow(BaseFlow):
    """
    Responsabilidad única: Orquestar el flujo de registro.
    
    Coordina los pasos del registro sin contener lógica de negocio compleja.
    Delega todas las operaciones específicas a componentes especializados.
    """

    def __init__(self):
        super().__init__()
        self.boki_api = BokiApi()
        self.steps = RegistrationSteps(self.boki_api)

    async def process_message(self, state: Dict, message: str, contact_id: str) -> Tuple[Dict, str, bool]:
        """
        Procesa un mensaje en el flujo de registro.
        
        Responsabilidad: Solo orquestar y delegar a componentes especializados.
        
        Args:
            state: Estado actual de la conversación
            message: Mensaje del usuario
            contact_id: ID del contacto
            
        Returns:
            Tuple[Dict, str, bool]: (nuevo_estado, respuesta, flujo_completado)
        """
        current_step = state.get("step", "waiting_id")
        data = state.get("data", {})

        # Usar logging estandarizado del BaseFlow
        self.log_step(current_step, contact_id, message)

        try:
            # Mapeo simple de pasos a métodos - Solo orquestación
            if current_step == "waiting_id":
                return await self.steps.process_document_step(message, data)
            elif current_step == "waiting_name":
                return await self.steps.process_name_step(message, data, contact_id)
            else:
                # Paso desconocido, reiniciar usando el componente de pasos
                self.logger.warning(f"Paso desconocido: {current_step}")
                return await self.steps._restart_registration(data.get("phone", ""))

        except Exception as e:
            # Error inesperado, usar logging del BaseFlow y delegar reinicio
            self.logger.error(f"Error procesando mensaje: {e}", exc_info=True)
            return await self.steps._restart_registration(data.get("phone", ""))