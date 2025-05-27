import logging
from typing import Optional, Dict, Any

from app.services.external import BokiApi
from app.services.intent_detection.detector import Intent, EnhancedIntentDetector
from app.services.conversation.unknown_handler import UnknownIntentHandler

logger = logging.getLogger(__name__)

class FlowRouter:
    """
    Responsabilidad única: Enrutar mensajes al flujo apropiado.
    """

    def __init__(self, flows: Dict, boki_api: BokiApi):
        """
        Inicializa el router de flujos.
        
        Args:
            flows: Diccionario con los flujos disponibles
            boki_api: Instancia de BokiApi para operaciones de API
        """
        self.flows = flows
        self.boki_api = boki_api
        self.intent_detector = EnhancedIntentDetector()
        self.unknown_handler = UnknownIntentHandler()

    async def route_message(self, contact_id: str, phone_number: str, message_text: str, is_registered: bool, conversation_state: Optional[Dict] = None) -> str:
        """Enruta el mensaje al flujo apropiado."""
        
        # Flujo activo tiene prioridad
        if conversation_state:
            return await self._process_active_flow(contact_id, conversation_state, message_text)

        # Usuario no registrado -> registro
        if not is_registered:
            return await self._start_registration_flow(contact_id, phone_number)

        # Usuario registrado -> detectar intención
        return await self._handle_registered_user(contact_id, phone_number, message_text)

    async def _process_active_flow(self, contact_id: str, conversation_state: Dict, message_text: str) -> str:
        """Procesa un mensaje en un flujo activo."""
        try:
            state_data = conversation_state.get("_doc", conversation_state)
            active_flow = state_data.get("flow")
            flow_state = state_data.get("state", {})

            flow_handler = self.flows.get(active_flow)
            if not flow_handler:
                await self.boki_api.clear_conversation_state(contact_id)
                return "Lo siento, algo salió mal. ¿En qué puedo ayudarte?"

            # Procesar mensaje en el flujo
            new_state, response, is_completed = await flow_handler.process_message(
                flow_state, message_text, contact_id
            )

            # Actualizar estado
            if is_completed:
                await self.boki_api.clear_conversation_state(contact_id)
            elif new_state:
                await self.boki_api.save_conversation_state(
                    contact_id, active_flow, new_state
                )

            return response

        except Exception as e:
            await self.boki_api.clear_conversation_state(contact_id)
            return "Hubo un error. ¿En qué puedo ayudarte?"

    async def _handle_registered_user(self, contact_id: str, phone_number: str, message_text: str) -> str:
        """Maneja mensajes de usuarios registrados basado en intención."""
        try:
            intent = self.intent_detector.detect_intent(message_text)
            
            flow_mapping = {
                Intent.FAQ: "faq",
                Intent.APPOINTMENT: "appointment", 
                Intent.END_CONVERSATION: "end_conversation",
                Intent.SUPPORT: "support"
            }
            
            flow_name = flow_mapping.get(intent)
            if flow_name:
                return await self._start_flow(flow_name, contact_id, phone_number, message_text)
            
            # Intención desconocida
            return self.unknown_handler.handle_unknown_intent(message_text, contact_id)

        except Exception as e:
            return "¿En qué puedo ayudarte?"

    async def _start_registration_flow(self, contact_id: str, phone_number: str) -> str:
        """Inicia el flujo de registro para usuarios no registrados."""
        try:
            initial_state = {"step": "waiting_id", "data": {"phone": phone_number}}
            
            success = await self.boki_api.save_conversation_state(
                contact_id, "registration", initial_state
            )
            
            if not success:
                return "Hay un problema técnico. Intenta de nuevo más tarde."

            return (
                "¡Hola! 👋 Parece que eres nuevo aquí.\n\n"
                "Para poder ayudarte mejor, necesito que te registres.\n\n"
                "Por favor, proporciona tu número de documento de identidad:"
            )

        except Exception as e:
            return "Hubo un error. Intenta de nuevo más tarde."

    async def _start_flow(self, flow_name: str, contact_id: str, phone_number: str, message_text: str) -> str:
        """Inicia un flujo específico."""
        try:
            flow_handler = self.flows.get(flow_name)
            if not flow_handler:
                return "Lo siento, no puedo procesar esa solicitud ahora."

            new_state, response, is_completed = await flow_handler.process_message(
                {}, message_text, contact_id
            )

            if not is_completed and new_state:
                await self.boki_api.save_conversation_state(
                    contact_id, flow_name, new_state
                )

            return response

        except Exception as e:
            return "Hubo un error procesando tu solicitud."
