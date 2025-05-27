import re
import logging
from typing import Optional, Dict

from app.services.external import BokiApi
from app.services.conversation.flows.base_flow import BaseFlow

logger = logging.getLogger(__name__)

class ButtonHandler:
    """
    Responsabilidad única: Detectar y manejar IDs de botones de WhatsApp.
    """

    # Patrones de botones conocidos
    BUTTON_PATTERNS = [
        r'^cat_id_\d+$',      # cat_id_1, cat_id_2, etc.
        r'^srv_id_\d+$',      # srv_id_1, srv_id_2, etc.
        r'^prof_id_\d+$',     # prof_id_1, prof_id_2, etc.
        r'^date_\d+$',        # date_1, date_2, etc.
        r'^time_\d+$',        # time_1, time_2, etc.
        r'^confirm_(yes|no)$', # confirm_yes, confirm_no
        r'^date_more$',       # date_more
        r'^date_back$',       # date_back
    ]

    def __init__(self, flows: Dict[str, BaseFlow], boki_api: BokiApi):
        """
        Inicializa el manejador de botones.
        
        Args:
            flows: Diccionario con los flujos disponibles (nombre -> BaseFlow)
            boki_api: Instancia de BokiApi para operaciones de API
        """
        self.flows = flows
        self.boki_api = boki_api
        logger.debug("[BUTTON_HANDLER] Inicializado correctamente")

    def is_button_id(self, message: str) -> bool:
        """Detecta si un mensaje es un ID de botón."""
        if not message:
            return False
        message = message.strip()
        return any(re.match(pattern, message) for pattern in self.BUTTON_PATTERNS)

    async def handle_button_without_state(self, contact_id: str, button_id: str) -> str:
        """
        Maneja un ID de botón cuando no hay estado de conversación.
        Intenta reconstruir el contexto o sugiere reiniciar.
        """
        try:
            if button_id.startswith('cat_id_'):
                return await self._handle_category_button(contact_id, button_id)
            
            # Para otros tipos de botones, no podemos reconstruir el contexto
            return self._get_context_lost_message(button_id)

        except Exception as e:
            return "Hubo un error. Por favor, intenta nuevamente."

    async def _handle_category_button(self, contact_id: str, button_id: str) -> str:
        """
        Maneja específicamente botones de categoría reconstruyendo el contexto.
        """
        try:
            # Extraer ID de categoría
            category_id = int(button_id.replace('cat_id_', ''))
            
            # Obtener flujo de appointment
            flow_handler = self.flows.get("appointment")
            if not flow_handler:
                return self._get_context_lost_message(button_id)

            # Simular estado inicial
            initial_state, _, _ = await flow_handler.process_message(
                {}, "agendar", contact_id
            )
            
            if initial_state and initial_state.get("step") == "waiting_category":
                # Procesar selección de categoría
                new_state, response, is_completed = await flow_handler.process_message(
                    initial_state, button_id, contact_id
                )
                
                # Guardar estado si no se completó
                if not is_completed and new_state:
                    await self.boki_api.save_conversation_state(
                        contact_id, "appointment", new_state
                    )
                
                return response
            
        except (ValueError, Exception) as e:
            return self._get_context_lost_message(button_id)

    def _get_context_lost_message(self, button_id: str) -> str:
        """Retorna mensaje apropiado cuando se pierde el contexto."""
        if button_id.startswith(('srv_id_', 'prof_id_', 'date_', 'time_', 'confirm_')):
            return (
                "Lo siento, parece que se perdió el contexto de la conversación. "
                "Por favor, vuelve a iniciar el proceso escribiendo 'agendar'."
            )
        
        return "No entiendo ese comando. ¿En qué puedo ayudarte?"
