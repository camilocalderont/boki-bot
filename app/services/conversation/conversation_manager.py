import logging
from app.services.intent_detection.detector import Intent, IntentDetector
from app.services.boki_api import BokiApi
from app.services.conversation.flows.registration_flow import RegistrationFlow
from app.services.conversation.flows.faq_flow import FAQFlow
from app.services.conversation.flows.appointment_flow import AppointmentFlow
from app.services.conversation.flows.end_conversation_flow import EndConversationFlow

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Gestiona los flujos de conversación según la intención detectada
    y el estado del usuario (registrado o no).
    """

    def __init__(self):
        self.intent_detector = IntentDetector()
        self.boki_api = BokiApi()

        # Inicializar flujos de conversación
        self.registration_flow = RegistrationFlow()
        self.faq_flow = FAQFlow()
        self.appointment_flow = AppointmentFlow()
        self.end_conversation_flow = EndConversationFlow()

        # Estado de conversación por usuario
        # {phone_number: {"flow": "registration", "step": "waiting_id", "data": {}}}
        self.conversations = {}

    async def process_message(self, phone_number: str, message_text: str):
        """
        Procesa un mensaje entrante y determina qué flujo debe seguir.

        Args:
            phone_number: Número de teléfono del remitente.
            message_text: Texto del mensaje.

        Returns:
            str: La respuesta que se enviará al usuario.
        """
        logger.info(f"Procesando mensaje de {phone_number}: {message_text}")

        # Verificar si el usuario está en un flujo activo
        if phone_number in self.conversations:
            active_flow = self.conversations[phone_number]["flow"]
            flow_state = self.conversations[phone_number]["state"]

            # Continuar flujo activo
            if active_flow == "registration":
                response, new_state, flow_completed = await self.registration_flow.process_message(
                    phone_number, message_text, flow_state
                )
            elif active_flow == "faq":
                response, new_state, flow_completed = await self.faq_flow.process_message(
                    phone_number, message_text, flow_state
                )
            elif active_flow == "appointment":
                response, new_state, flow_completed = await self.appointment_flow.process_message(
                    phone_number, message_text, flow_state
                )
            elif active_flow == "end_conversation":
                response, new_state, flow_completed = await self.end_conversation_flow.process_message(
                    phone_number, message_text, flow_state
                )
            else:
                # Flujo desconocido, reiniciar
                return await self._handle_new_interaction(phone_number, message_text)

            # Actualizar o eliminar estado según si el flujo ha terminado
            if flow_completed:
                if phone_number in self.conversations:
                    del self.conversations[phone_number]
            else:
                self.conversations[phone_number]["state"] = new_state

            return response

        # Nueva interacción - verificar si el usuario está registrado
        return await self._handle_new_interaction(phone_number, message_text)

    async def _handle_new_interaction(self, phone_number: str, message_text: str):
        """Maneja una nueva interacción, verificando si el usuario está registrado."""
        # Verificar si el usuario está registrado
        client = await self.boki_api.get_client_by_phone(phone_number)

        if client:
            # Usuario registrado, detectar intención
            return await self._handle_registered_user(phone_number, message_text)
        else:
            # Usuario no registrado, iniciar flujo de registro
            return await self._start_registration_flow(phone_number)

    async def _handle_registered_user(self, phone_number: str, message_text: str):
        """Maneja el mensaje de un usuario registrado basado en la intención."""
        intent = self.intent_detector.detect_intent(message_text)

        if intent == Intent.FAQ:
            return await self._start_faq_flow(phone_number, message_text)
        elif intent == Intent.APPOINTMENT:
            return await self._start_appointment_flow(phone_number, message_text)
        elif intent == Intent.END_CONVERSATION:
            return await self._start_end_conversation_flow(phone_number, message_text)
        else:
            # Intención desconocida, mensaje genérico
            return ("No entendí lo que necesitas. ¿Quieres hacer una pregunta, "
                   "agendar una cita o finalizar la conversación?")

    async def _start_registration_flow(self, phone_number: str):
        """Inicia el flujo de registro para un usuario no registrado."""
        self.conversations[phone_number] = {
            "flow": "registration",
            "state": {"step": "waiting_id", "data": {}}
        }

        return ("Parece que no estás registrado en nuestro sistema. "
               "Por favor, proporciona tu número de documento de identidad:")

    async def _start_faq_flow(self, phone_number: str, message_text: str):
        """Inicia el flujo de preguntas frecuentes."""
        response, state, completed = await self.faq_flow.process_message(
            phone_number, message_text, {}
        )

        if not completed:
            self.conversations[phone_number] = {
                "flow": "faq",
                "state": state
            }

        return response

    async def _start_appointment_flow(self, phone_number: str, message_text: str):
        """Inicia el flujo de agendamiento de citas."""
        response, state, completed = await self.appointment_flow.process_message(
            phone_number, message_text, {}
        )

        if not completed:
            self.conversations[phone_number] = {
                "flow": "appointment",
                "state": state
            }

        return response

    async def _start_end_conversation_flow(self, phone_number: str, message_text: str):
        """Inicia el flujo de fin de conversación."""
        response, _, _ = await self.end_conversation_flow.process_message(
            phone_number, message_text, {}
        )

        return response