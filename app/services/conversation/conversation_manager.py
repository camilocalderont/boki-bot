import logging
from typing import Optional, Dict
from app.services.external import BokiApi
from app.services.conversation.flows import (BaseFlow, RegistrationFlow, FAQFlow, AppointmentFlow, EndConversationFlow, SupportFlow)
from app.services.conversation.message_processor import MessageProcessor
from app.services.conversation.button_handler import ButtonHandler
from app.services.conversation.flow_router import FlowRouter

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Responsabilidad única: Orquestar el procesamiento de conversaciones.
    Coordina los diferentes componentes especializados.
    """

    def __init__(self):
        """
        Inicializa el gestor de conversaciones.
        Configura todos los flujos y componentes necesarios.
        """
        # APIs y recursos
        self.boki_api = BokiApi()
        
        # Flujos de conversación
        self.flows: Dict[str, BaseFlow] = {
            "registration": RegistrationFlow(),
            "faq": FAQFlow(),
            "appointment": AppointmentFlow(),
            "end_conversation": EndConversationFlow(),
            "support": SupportFlow()
        }
        
        # Componentes especializados
        self.message_processor = MessageProcessor(self.boki_api)
        self.button_handler = ButtonHandler(self.flows, self.boki_api)
        self.flow_router = FlowRouter(self.flows, self.boki_api)

    async def process_message(self, phone_number: str, message_text: str, message_id: Optional[str] = None) -> Optional[str]:
        """
        Procesa un mensaje entrante de forma simplificada.
        Responsabilidad única: orquestar el flujo general.
        """
        try:
            logger.info(f"Procesando mensaje de {phone_number}")

            # 1. Procesar mensaje entrante
            message_data = await self.message_processor.process_incoming_message(
                phone_number, message_text, message_id
            )

            # 2. Validar resultado del procesamiento
            if message_data.get("is_duplicate"):
                return None
                
            if message_data.get("error"):
                return self._get_error_response(message_data["error"])

            # 3. Manejar botones sin estado de conversación
            if (not message_data["conversation_state"] and 
                self.button_handler.is_button_id(message_text)):
                
                response = await self.button_handler.handle_button_without_state(
                    message_data["contact_id"], message_text
                )
            else:
                # 4. Enrutar a flujo apropiado
                response = await self.flow_router.route_message(
                    contact_id=message_data["contact_id"],
                    phone_number=message_data["phone_number"], 
                    message_text=message_data["message_text"],
                    is_registered=message_data["is_registered"],
                    conversation_state=message_data["conversation_state"]
                )

            # 5. Registrar respuesta
            if response and message_id:
                await self.message_processor.log_outgoing_message(
                    message_data["contact_id"], response
                )

            return response

        except Exception as e:
            return "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo."

    def _get_error_response(self, error_type: str) -> str:
        """Retorna respuesta apropiada según el tipo de error."""
        error_responses = {
            "contact_error": "Lo siento, hay un problema técnico. Intenta de nuevo más tarde.",
            "processing_error": "Hubo un error procesando tu mensaje. Por favor intenta de nuevo."
        }
        return error_responses.get(error_type, "Error desconocido. Intenta de nuevo.")

    async def close(self):
        """Cierra recursos del manager."""
        try:
            await self.boki_api.close()
            logger.debug("Recursos cerrados exitosamente")
        except Exception as e:
            logger.error(f"Error cerrando recursos: {e}")